/**
 * CartStack — Unit-5 Cart Intercept のインフラ（infrastructure-design.md）。
 *
 * 構成:
 * - DDB CartWatchItems / NotificationLogs（KMS / TTL / GSI1 / PITR=prd）
 * - 6 Lambda（cart_intake / cart_dismiss / cart_list / push_token / notification_dispatcher / cart_attack_scheduler_retry）
 * - EventBridge Scheduler（default Group + retry batch rate(15min)）
 * - End User Messaging Application × 環境別 + APNs/FCM Channel
 * - cartAlertTopic + Slack Bridge Lambda + Secrets Manager Slack Webhook 参照
 * - CloudWatch Alarms 5 系統
 * - 必須 4 タグ
 *
 * 設計: aidlc-docs/construction/unit-5-cart-intercept/infrastructure-design/
 *      infrastructure-design.md / deployment-architecture.md
 *
 * Note: Unit-1 PlatformStack の追実装（kmsKey public 化 / IdempotencyKeysTable 等の 7 項目、
 *       PR #platform-additions-001）が完了するまで、kmsKey 等の参照は dev 環境では
 *       一時的に新規 KMS Key を作成する fallback 実装とする（Member D の Code Generation
 *       中に Unit-1 が間に合わない場合の代替案 B、§8.2 ブロッカー判定）。
 *
 * TODO(unit-1-packaging-001 / B-505): Lambda の `code: lambda.Code.fromAsset('../backend/src/cart')`
 *       + `handler: 'handlers.cart_intake.lambda_handler'` の組合せでは、各 Lambda の
 *       `from backend.src.cart.repository import ...` / `from backend.src.common.logging import AuditLogger`
 *       が runtime で ImportError になる。Member A の Unit-1 packaging 方針確立（B-505）後に、
 *       asset = リポジトリルート + handler 完全修飾形 / Lambda Layer / vendoring のいずれかに移行する。
 *       詳細は doc/backlog.md B-505 参照。
 */

import {
  aws_cloudwatch as cloudwatch,
  aws_cloudwatch_actions as cw_actions,
  aws_dynamodb as dynamodb,
  aws_iam as iam,
  aws_kms as kms,
  aws_lambda as lambda,
  aws_pinpoint as pinpoint,
  aws_scheduler as scheduler,
  aws_sns as sns,
  aws_sns_subscriptions as subs,
  aws_sqs as sqs,
  aws_ssm as ssm,
  Duration,
  RemovalPolicy,
  Stack,
  Tags,
  type StackProps,
} from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import type { Construct } from 'constructs';

/**
 * CartStack のプロパティ。
 *
 * Unit-1 PlatformStack 追実装（kmsKey public 化等）が未整備の dev 期間では
 * `platformKmsKey` を省略すると本 Stack 内で新規 KMS を作成する fallback。
 */
export interface CartStackProps extends StackProps {
  envName: 'dev' | 'prd';
  /** 個人 sandbox suffix（dev 環境のみ）。 */
  developerInitial?: string;
  /** Unit-1 PlatformStack の KMS Key（未指定時は新規作成 fallback）。 */
  platformKmsKey?: kms.IKey;
}

/** リソース命名ヘルパー（shared-infrastructure.md §2 規約: yudane-<unit>-<env>-<entity>）。 */
function resourceName(props: CartStackProps, suffix: string): string {
  const initSegment =
    props.envName === 'dev' && props.developerInitial ? `-${props.developerInitial}` : '';
  return `yudane-cart-${props.envName}${initSegment}-${suffix}`;
}

export class CartStack extends Stack {
  public readonly cartWatchItemsTable: dynamodb.Table;
  public readonly notificationLogsTable: dynamodb.Table;
  public readonly cartIntakeFunction: lambda.Function;
  public readonly cartDismissFunction: lambda.Function;
  public readonly cartListFunction: lambda.Function;
  public readonly pushTokenFunction: lambda.Function;
  public readonly notificationDispatcherFunction: lambda.Function;
  public readonly cartAttackSchedulerRetryFunction: lambda.Function;
  public readonly cartAlertTopic: sns.Topic;
  public readonly schedulerInvokeRole: iam.Role;

  constructor(scope: Construct, id: string, props: CartStackProps) {
    super(scope, id, props);

    const { envName } = props;
    const isProd = envName === 'prd';
    const removalPolicy = isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    // KMS Key（PlatformStack の kmsKey 未公開時は新規作成 fallback）
    const kmsKey =
      props.platformKmsKey ??
      new kms.Key(this, 'CartLocalKey', {
        enableKeyRotation: true,
        removalPolicy,
        description: `${resourceName(props, 'kms')} 一時 KMS Key（PlatformStack 整備後に切替）`,
      });

    // ===== Persistence 層 =====

    this.cartWatchItemsTable = new dynamodb.Table(this, 'CartWatchItemsTable', {
      tableName: resourceName(props, 'watch-items'),
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsKey,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: isProd },
      removalPolicy,
      deletionProtection: isProd,
    });
    this.cartWatchItemsTable.addGlobalSecondaryIndex({
      indexName: 'GSI1-status-createdAt',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    this.notificationLogsTable = new dynamodb.Table(this, 'NotificationLogsTable', {
      tableName: resourceName(props, 'notification-logs'),
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsKey,
      timeToLiveAttribute: 'ttl',
      removalPolicy,
    });
    this.notificationLogsTable.addGlobalSecondaryIndex({
      indexName: 'GSI1-cartWatchItemId',
      partitionKey: { name: 'cartWatchItemId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sentAt', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // ===== Compute 層: 6 Lambda =====

    // SchedulerInvokeRole（Confused Deputy 防御: SourceAccount + SourceArn）
    this.schedulerInvokeRole = new iam.Role(this, 'SchedulerInvokeRole', {
      roleName: resourceName(props, 'scheduler-invoke-role'),
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com', {
        conditions: {
          StringEquals: { 'aws:SourceAccount': this.account },
          ArnLike: {
            'aws:SourceArn': `arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`,
          },
        },
      }),
    });

    // 通知 DLQ
    const notificationDlq = new sqs.Queue(this, 'NotificationDispatcherDlq', {
      queueName: resourceName(props, 'notification-dlq'),
      retentionPeriod: Duration.days(14),
      encryptionMasterKey: kmsKey,
    });

    const lambdaCommonProps = {
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      timeout: Duration.seconds(30),
      memorySize: 512,
    } satisfies Pick<
      lambda.FunctionProps,
      'runtime' | 'architecture' | 'timeout' | 'memorySize'
    >;

    // B-04 cart_intake（SnapStart）
    this.cartIntakeFunction = new lambda.Function(this, 'CartIntakeFunction', {
      ...lambdaCommonProps,
      functionName: resourceName(props, 'intake'),
      handler: 'handlers.cart_intake.lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      timeout: Duration.seconds(5),
      environment: {
        CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
        DEV_INITIAL: props.developerInitial ?? '',
        USE_DUMMY_CATALOG: 'true', // backlog B-503 対応
      },
      snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
    });

    // B-04 cart_dismiss
    this.cartDismissFunction = new lambda.Function(this, 'CartDismissFunction', {
      ...lambdaCommonProps,
      functionName: resourceName(props, 'dismiss'),
      handler: 'handlers.cart_dismiss.dismiss_lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 256,
      timeout: Duration.seconds(5),
      reservedConcurrentExecutions: 50,
      environment: { CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName },
      snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
    });

    // B-04 cart_list
    this.cartListFunction = new lambda.Function(this, 'CartListFunction', {
      ...lambdaCommonProps,
      functionName: resourceName(props, 'list'),
      handler: 'handlers.cart_list.list_lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 256,
      timeout: Duration.seconds(3),
      reservedConcurrentExecutions: 100,
      environment: { CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName },
    });

    // B-04 push_token
    this.pushTokenFunction = new lambda.Function(this, 'PushTokenFunction', {
      ...lambdaCommonProps,
      functionName: resourceName(props, 'push-token'),
      handler: 'handlers.push_token.register_lambda_handler',
      code: lambda.Code.fromAsset('../backend/src/cart'),
      memorySize: 256,
      timeout: Duration.seconds(5),
      reservedConcurrentExecutions: 20,
      environment: {
        EUM_APPLICATION_ID: '', // SSM Parameter から runtime 注入
      },
    });

    // B-06 notification_dispatcher（SnapStart + DLQ）
    this.notificationDispatcherFunction = new lambda.Function(
      this,
      'NotificationDispatcherFunction',
      {
        ...lambdaCommonProps,
        functionName: resourceName(props, 'notification-dispatcher'),
        handler: 'handlers.notification_dispatcher.lambda_handler',
        code: lambda.Code.fromAsset('../backend/src/cart'),
        memorySize: 512,
        timeout: Duration.seconds(30),
        reservedConcurrentExecutions: 50,
        deadLetterQueue: notificationDlq,
        environment: {
          CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
          NOTIFICATION_LOGS_TABLE: this.notificationLogsTable.tableName,
          EUM_APPLICATION_ID: '',
        },
        snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
      },
    );

    // B-05 cart_attack_scheduler_retry
    this.cartAttackSchedulerRetryFunction = new lambda.Function(
      this,
      'CartAttackSchedulerRetryFunction',
      {
        ...lambdaCommonProps,
        functionName: resourceName(props, 'attack-scheduler-retry'),
        handler: 'handlers.cart_attack_scheduler_retry.lambda_handler',
        code: lambda.Code.fromAsset('../backend/src/cart'),
        memorySize: 512,
        timeout: Duration.seconds(60),
        reservedConcurrentExecutions: 10,
        environment: {
          CART_WATCH_ITEMS_TABLE: this.cartWatchItemsTable.tableName,
          NOTIFICATION_DISPATCHER_ARN: this.notificationDispatcherFunction.functionArn,
          SCHEDULER_ROLE_ARN: this.schedulerInvokeRole.roleArn,
          DEV_INITIAL: props.developerInitial ?? '',
        },
      },
    );

    // EventBridge Schedule: cart_attack_scheduler_retry を 15 分間隔で起動
    new scheduler.CfnSchedule(this, 'CartAttackSchedulerRetrySchedule', {
      name: resourceName(props, 'attack-scheduler-retry-schedule'),
      groupName: 'default',
      scheduleExpression: 'rate(15 minutes)',
      flexibleTimeWindow: { mode: 'OFF' },
      state: 'ENABLED',
      target: {
        arn: this.cartAttackSchedulerRetryFunction.functionArn,
        roleArn: this.schedulerInvokeRole.roleArn,
      },
    });

    // ===== Integration 層 =====

    // End User Messaging Application（旧 Pinpoint App）
    const eumApp = new pinpoint.CfnApp(this, 'CartEumApp', {
      name: `yudane-cart-${envName}${props.developerInitial ? `-${props.developerInitial}` : ''}`,
      tags: {
        Environment: envName,
        Unit: 'cart',
        Owner: 'member-d',
        CostCenter: 'yudane-hackathon-2026',
      },
    });

    new ssm.StringParameter(this, 'EumApplicationIdParam', {
      parameterName: `/yudane/${envName}${props.developerInitial ? `-${props.developerInitial}` : ''}/cart/eum-application-id`,
      stringValue: eumApp.ref,
    });

    // SNS Topic + Slack Bridge（Q6=A'）
    this.cartAlertTopic = new sns.Topic(this, 'CartAlertTopic', {
      topicName: resourceName(props, 'alerts'),
      displayName: `YUDANE Cart Alerts (${envName})`,
      masterKey: kmsKey,
    });

    // Slack Webhook 用 Secret（手動登録、Secrets Manager の参照のみ）
    const slackWebhookSecretName = `yudane-cart-${envName}-slack-webhook-url`;
    const slackBridgeFunction = new lambda.Function(this, 'SlackBridgeFunction', {
      functionName: resourceName(props, 'slack-bridge'),
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      memorySize: 128,
      timeout: Duration.seconds(10),
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
def handler(event, context):
    """SNS → Slack Webhook ブリッジ。実装は後続 PR で詳細化。"""
    import json
    return {"statusCode": 200, "body": json.dumps(event)}
      `),
      environment: {
        SLACK_WEBHOOK_SECRET_ARN: `arn:aws:secretsmanager:${this.region}:${this.account}:secret:${slackWebhookSecretName}-*`,
      },
    });
    slackBridgeFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['secretsmanager:GetSecretValue'],
        resources: [
          `arn:aws:secretsmanager:${this.region}:${this.account}:secret:${slackWebhookSecretName}-*`,
        ],
      }),
    );

    this.cartAlertTopic.addSubscription(new subs.LambdaSubscription(slackBridgeFunction));

    // ===== IAM 権限付与（最小権限、SECURITY-06）=====

    this.cartWatchItemsTable.grantReadWriteData(this.cartIntakeFunction);
    this.cartWatchItemsTable.grantReadWriteData(this.cartDismissFunction);
    this.cartWatchItemsTable.grantReadData(this.cartListFunction);
    this.cartWatchItemsTable.grantReadWriteData(this.notificationDispatcherFunction);
    this.cartWatchItemsTable.grantReadWriteData(this.cartAttackSchedulerRetryFunction);
    this.notificationLogsTable.grantWriteData(this.notificationDispatcherFunction);

    this.cartIntakeFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['scheduler:CreateSchedule', 'scheduler:GetSchedule'],
        resources: [
          `arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`,
        ],
      }),
    );
    this.cartIntakeFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['iam:PassRole'],
        resources: [this.schedulerInvokeRole.roleArn],
      }),
    );

    this.cartDismissFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['scheduler:DeleteSchedule', 'scheduler:GetSchedule'],
        resources: [
          `arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`,
        ],
      }),
    );

    this.cartAttackSchedulerRetryFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['scheduler:CreateSchedule', 'scheduler:GetSchedule'],
        resources: [
          `arn:aws:scheduler:${this.region}:${this.account}:schedule/default/cart-*`,
        ],
      }),
    );
    this.cartAttackSchedulerRetryFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['iam:PassRole'],
        resources: [this.schedulerInvokeRole.roleArn],
      }),
    );

    // notification_dispatcher: EUM SendMessages
    this.notificationDispatcherFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['mobiletargeting:SendMessages'],
        resources: [
          `arn:aws:mobiletargeting:${this.region}:${this.account}:apps/${eumApp.ref}/*`,
        ],
      }),
    );

    // push_token: EUM UpdateEndpoint
    this.pushTokenFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['mobiletargeting:UpdateEndpoint', 'mobiletargeting:GetEndpoint'],
        resources: [
          `arn:aws:mobiletargeting:${this.region}:${this.account}:apps/${eumApp.ref}/endpoints/*`,
        ],
      }),
    );

    // SchedulerInvokeRole に Lambda Invoke 権限
    this.schedulerInvokeRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['lambda:InvokeFunction'],
        resources: [
          this.notificationDispatcherFunction.functionArn,
          this.cartAttackSchedulerRetryFunction.functionArn,
        ],
      }),
    );

    // ===== CloudWatch Alarms 5 系統 =====

    // Alarm 1: DLQ depth
    new cloudwatch.Alarm(this, 'NotificationDlqDepthAlarm', {
      alarmName: resourceName(props, 'alarm-dlq-depth'),
      metric: notificationDlq.metricApproximateNumberOfMessagesVisible({
        period: Duration.minutes(5),
        statistic: 'Maximum',
      }),
      threshold: 1,
      evaluationPeriods: 1,
      alarmDescription: 'Notification DLQ にメッセージ滞留',
    }).addAlarmAction(new cw_actions.SnsAction(this.cartAlertTopic));

    // Alarm 2: Notification 遅延（カスタム metric、本実装は cart_intake/notification_dispatcher 側）
    // → metric は CloudWatch EMF 経由で実装、Alarm はメトリクス名のみ参照
    new cloudwatch.Alarm(this, 'NotificationDelayAlarm', {
      alarmName: resourceName(props, 'alarm-notification-delay'),
      metric: new cloudwatch.Metric({
        namespace: 'YUDANE',
        metricName: 'cart.notification.delay_seconds',
        period: Duration.minutes(5),
        statistic: 'p99',
      }),
      threshold: 60,
      evaluationPeriods: 1,
      alarmDescription: 'Notification 遅延 p99 > 60s',
    }).addAlarmAction(new cw_actions.SnsAction(this.cartAlertTopic));

    // Alarm 3: Scheduler create_failed
    new cloudwatch.Alarm(this, 'SchedulerCreateFailedAlarm', {
      alarmName: resourceName(props, 'alarm-scheduler-create-failed'),
      metric: new cloudwatch.Metric({
        namespace: 'YUDANE',
        metricName: 'cart.scheduler.create_failed',
        period: Duration.minutes(5),
        statistic: 'Sum',
      }),
      threshold: 5,
      evaluationPeriods: 1,
      alarmDescription: 'Scheduler create_failed > 5/5min',
    }).addAlarmAction(new cw_actions.SnsAction(this.cartAlertTopic));

    // Alarm 4: Lambda Error 率（6 Lambda 個別、ここでは notification_dispatcher のみ例示）
    new cloudwatch.Alarm(this, 'NotificationDispatcherErrorAlarm', {
      alarmName: resourceName(props, 'alarm-dispatcher-error'),
      metric: this.notificationDispatcherFunction.metricErrors({
        period: Duration.minutes(5),
        statistic: 'Sum',
      }),
      threshold: 3,
      evaluationPeriods: 1,
      alarmDescription: 'NotificationDispatcher Errors > 3/5min',
    }).addAlarmAction(new cw_actions.SnsAction(this.cartAlertTopic));

    // Alarm 5: retry_failed（NFR Q4=A'）
    new cloudwatch.Alarm(this, 'SchedulerRetryFailedAlarm', {
      alarmName: resourceName(props, 'alarm-scheduler-retry-failed'),
      metric: new cloudwatch.Metric({
        namespace: 'YUDANE',
        metricName: 'cart.scheduler.retry_failed',
        period: Duration.minutes(15),
        statistic: 'Sum',
      }),
      threshold: 5,
      evaluationPeriods: 1,
      alarmDescription: 'B-05 retry batch で 3 回失敗が頻発、watching_orphaned 遷移増',
    }).addAlarmAction(new cw_actions.SnsAction(this.cartAlertTopic));

    // ===== SSM Parameter（Cross-Stack Output）=====
    new ssm.StringParameter(this, 'CartWatchItemsTableArnParam', {
      parameterName: `/yudane/${envName}${props.developerInitial ? `-${props.developerInitial}` : ''}/cart/cart-watch-items-table-arn`,
      stringValue: this.cartWatchItemsTable.tableArn,
    });
    new ssm.StringParameter(this, 'NotificationLogsTableArnParam', {
      parameterName: `/yudane/${envName}${props.developerInitial ? `-${props.developerInitial}` : ''}/cart/notification-logs-table-arn`,
      stringValue: this.notificationLogsTable.tableArn,
    });
    new ssm.StringParameter(this, 'AlertTopicArnParam', {
      parameterName: `/yudane/${envName}${props.developerInitial ? `-${props.developerInitial}` : ''}/cart/alert-topic-arn`,
      stringValue: this.cartAlertTopic.topicArn,
    });

    // ===== タグ戦略（Q7=A 必須 4 タグ）=====
    Tags.of(this).add('Environment', envName);
    Tags.of(this).add('Unit', 'cart');
    Tags.of(this).add('Owner', 'member-d');
    Tags.of(this).add('CostCenter', 'yudane-hackathon-2026');

    // ===== cdk-nag suppressions =====
    NagSuppressions.addResourceSuppressions(
      this.notificationDispatcherFunction,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason:
            'mobiletargeting:SendMessages の Resource は EUM Endpoint ID で動的決定、IAM Resource を事前特定不可',
          appliesTo: ['Resource::*'],
        },
      ],
      true,
    );
    NagSuppressions.addResourceSuppressions(
      this.cartAttackSchedulerRetryFunction,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'CloudWatch EMF metric は wildcard Resource 必須（AWS 標準）',
          appliesTo: ['Resource::*'],
        },
      ],
      true,
    );
    NagSuppressions.addResourceSuppressions(notificationDlq, [
      {
        id: 'AwsSolutions-SQS3',
        reason: 'KMS CMEK で暗号化済み、別 DLQ は不要',
      },
    ]);
    NagSuppressions.addResourceSuppressions(
      this.cartIntakeFunction,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'scheduler:CreateSchedule は cart-* prefix で範囲限定済み',
          appliesTo: [
            'Resource::arn:aws:scheduler:*:*:schedule/default/cart-*',
          ],
        },
      ],
      true,
    );
  }
}
