/**
 * ReelStack — Unit-4 Reel（UC-02）。infrastructure-design.md / deployment-architecture.md。
 *
 * Unit-1 platform-stack の共有資源（KMS / SNS / API Gateway / Lambda Layer）を SSM 参照で
 * 継承し、reel 固有リソース（DynamoDB 2 テーブル / feed・transition Lambda / API パス /
 * usage plan 429 / Alarm）を追加する。MVP は VPC なし（ダミーカタログ）、決勝のみ
 * VPC 内 catalog Lambda を feature フラグで追加（本スタックでは MVP 構成を生成）。
 */

import {
  aws_apigateway as apigw,
  aws_cloudwatch as cloudwatch,
  aws_cloudwatch_actions as cwactions,
  aws_dynamodb as dynamodb,
  aws_kms as kms,
  aws_lambda as lambda,
  aws_sns as sns,
  aws_ssm as ssm,
  Duration,
  RemovalPolicy,
  Stack,
  type StackProps,
} from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import type { Construct } from 'constructs';

/** ReelStack のプロパティ。 */
export interface ReelStackProps extends StackProps {
  /** 環境名（dev / prd）。 */
  envName: string;
}

export class ReelStack extends Stack {
  constructor(scope: Construct, id: string, props: ReelStackProps) {
    super(scope, id, props);

    const { envName } = props;
    const isProd = envName === 'prd';
    const removalPolicy = isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    // --- platform-stack の共有資源を SSM 参照（Export/Import 不使用、§3）---
    const kmsKeyArn = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/kms-key-arn`,
    );
    const alertsTopicArn = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/alerts-topic-arn`,
    );
    const key = kms.Key.fromKeyArn(this, 'PlatformKey', kmsKeyArn);
    const alertsTopic = sns.Topic.fromTopicArn(this, 'AlertsTopic', alertsTopicArn);

    // --- DynamoDB: reel 所有 2 テーブル（Q2=A、共通設定は Unit-1 規約）---
    const transitions = new dynamodb.Table(this, 'AmazonTransitions', {
      tableName: `yudane-reel-${envName}-amazon-transitions`,
      partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'transitionId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: key,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      timeToLiveAttribute: 'ttl',
      removalPolicy,
    });
    // 月間集計 GSI（userId#monthBucket、北極星指標 / Safeguard カウント参照）
    transitions.addGlobalSecondaryIndex({
      indexName: 'gsi-month',
      partitionKey: { name: 'userMonth', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'recordedAt', type: dynamodb.AttributeType.STRING },
    });

    const impressions = new dynamodb.Table(this, 'ReelImpressions', {
      tableName: `yudane-reel-${envName}-impressions`,
      partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'shownAtCardId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: key,
      timeToLiveAttribute: 'ttl',
      removalPolicy,
    });

    // --- Lambda（VPC 外 + SnapStart、AuditLogger Layer は別途 SSM 参照で付与想定）---
    const commonProps = {
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      timeout: Duration.seconds(10),
      memorySize: 512,
      environment: {
        ENV_NAME: envName,
        TRANSITIONS_TABLE: transitions.tableName,
        IMPRESSIONS_TABLE: impressions.tableName,
        BEDROCK_MODEL_PARAM: `/yudane/${envName}/reel/bedrock-model-id`,
      },
    } as const;

    const feedFn = new lambda.Function(this, 'ReelFeedFn', {
      ...commonProps,
      functionName: `yudane-reel-${envName}-feed`,
      handler: 'reel.handlers.feed.handler',
      code: lambda.Code.fromInline('# placeholder; bundled in build phase'),
      snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
    });
    const feedAlias = new lambda.Alias(this, 'ReelFeedLive', {
      aliasName: 'live',
      version: feedFn.currentVersion,
    });

    const transitionFn = new lambda.Function(this, 'ReelTransitionFn', {
      ...commonProps,
      functionName: `yudane-reel-${envName}-transition`,
      handler: 'reel.handlers.transition.handler',
      code: lambda.Code.fromInline('# placeholder; bundled in build phase'),
      snapStart: lambda.SnapStartConf.ON_PUBLISHED_VERSIONS,
    });
    const transitionAlias = new lambda.Alias(this, 'ReelTransitionLive', {
      aliasName: 'live',
      version: transitionFn.currentVersion,
    });

    // reel 所有テーブルへの最小権限（SECURITY-06）
    transitions.grantReadWriteData(transitionFn);
    impressions.grantReadWriteData(feedFn);
    transitions.grantReadData(feedFn);

    // --- API Gateway: platform の単一 API にパス相乗り（Q4=A、fromRestApiAttributes）---
    const apiId = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/api-id`,
    );
    const rootResourceId = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/api-root-resource-id`,
    );
    const api = apigw.RestApi.fromRestApiAttributes(this, 'PlatformApi', {
      restApiId: apiId,
      rootResourceId,
    });
    const v1 = api.root.addResource('v1');
    v1.addResource('reel').addMethod('GET', new apigw.LambdaIntegration(feedAlias));
    v1
      .addResource('amazon-transitions')
      .addMethod('POST', new apigw.LambdaIntegration(transitionAlias));

    // usage plan（POST 429、SECURITY-11 / REEL-API-07）
    const plan = api.addUsagePlan('ReelUsagePlan', {
      name: `yudane-reel-${envName}-usage`,
      throttle: { rateLimit: 20, burstLimit: 40 },
    });
    plan.addApiStage({ stage: api.deploymentStage });

    // --- reel 固有 SSM 設定 ---
    new ssm.StringParameter(this, 'BedrockModelParam', {
      parameterName: `/yudane/${envName}/reel/bedrock-model-id`,
      stringValue: 'anthropic.claude-haiku-4-5',
    });
    new ssm.StringParameter(this, 'CreatorsApprovedParam', {
      parameterName: `/yudane/${envName}/reel/creators-approved`,
      stringValue: 'false',
    });
    new ssm.StringParameter(this, 'TransitionsTableParam', {
      parameterName: `/yudane/${envName}/reel/transitions-table-name`,
      stringValue: transitions.tableName,
    });

    // --- Alarm → platform SNS（NFR-OBS / SECURITY-14）---
    this.addErrorAlarm('ReelFeedErrors', feedFn, alertsTopic);
    this.addErrorAlarm('ReelTransitionErrors', transitionFn, alertsTopic);

    this.applyNagSuppressions();
  }

  /** Lambda エラー率 Alarm を platform SNS に接続する。 */
  private addErrorAlarm(id: string, fn: lambda.Function, topic: sns.ITopic): void {
    const alarm = new cloudwatch.Alarm(this, id, {
      metric: fn.metricErrors({ period: Duration.minutes(5) }),
      threshold: 5,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    alarm.addAlarmAction(new cwactions.SnsAction(topic));
  }

  /** cdk-nag の正当な抑制（理由コメント必須、tech-cdk §2）。 */
  private applyNagSuppressions(): void {
    NagSuppressions.addStackSuppressions(this, [
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'Lambda 実行ロールに付与される AWS 管理ポリシー（基本実行 / X-Ray）。MVP では許容、決勝前にカスタムポリシー化を検討（NFR-SEC SECURITY-06）',
      },
      {
        id: 'AwsSolutions-IAM5',
        reason:
          'DynamoDB grant が GSI に対して付与するワイルドカード（table/index/*）。テーブル単位に限定済みで意図的（最小権限の範囲内）',
      },
      {
        id: 'AwsSolutions-APIG4',
        reason:
          'reel パスは platform の Cognito Authorizer を継承（fromRestApiAttributes 経由のため本スタックの synth では検出されない）。認可は platform-stack で担保',
      },
    ]);
  }
}
