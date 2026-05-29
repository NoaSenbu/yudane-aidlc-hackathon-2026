/**
 * AuthStack — Unit-2 Auth & Profile（infrastructure-design.md）。
 *
 * DynamoDB 4 テーブル / B-01 Cognito トリガー / B-08 EventBridge cron 2 本 / auth API Lambda。
 * platform-stack の SSM 出力（VPC/UserPool/KMS/SG）を参照する（shared-infrastructure.md）。
 */

import {
  aws_dynamodb as dynamodb,
  aws_events as events,
  aws_events_targets as targets,
  aws_kms as kms,
  aws_lambda as lambda,
  Duration,
  RemovalPolicy,
  Stack,
  type StackProps,
  aws_ssm as ssm,
} from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import type { Construct } from 'constructs';

/** AuthStack のプロパティ。 */
export interface AuthStackProps extends StackProps {
  envName: string;
}

export class AuthStack extends Stack {
  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    const { envName } = props;
    const isProd = envName === 'prd';
    const removalPolicy = isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    // platform-stack の出力を SSM 参照（Export/Import 不使用、tech-cdk §3）
    const kmsKeyArn = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/kms-key-arn`,
    );
    const key = kms.Key.fromKeyArn(this, 'PlatformKey', kmsKeyArn);

    // --- DynamoDB 4 テーブル（PK=userId、Q1=A）---
    const tableNames = ['users', 'preference-vectors', 'safeguard-states', 'achievements'] as const;
    const tables: Record<string, dynamodb.Table> = {};
    for (const name of tableNames) {
      tables[name] = new dynamodb.Table(this, `Table-${name}`, {
        tableName: `yudane-auth-${envName}-${name}`,
        partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        pointInTimeRecovery: true,
        encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
        encryptionKey: key,
        removalPolicy,
      });
    }

    // --- B-08 PreferenceVectorUpdater（日次/週次の別ハンドラ、Q3=A）---
    const commonLambdaProps = {
      runtime: lambda.Runtime.PYTHON_3_13,
      memorySize: 256,
      timeout: Duration.seconds(60),
      code: lambda.Code.fromAsset('../backend'),
      environment: {
        USERS_TABLE: tables.users.tableName,
        PREFERENCE_VECTORS_TABLE: tables['preference-vectors'].tableName,
        SAFEGUARD_STATES_TABLE: tables['safeguard-states'].tableName,
        ACHIEVEMENTS_TABLE: tables.achievements.tableName,
      },
    };

    const dailyBatch = new lambda.Function(this, 'PreferenceUpdaterDaily', {
      ...commonLambdaProps,
      handler: 'src.auth.preference_updater.handler',
      functionName: `yudane-auth-${envName}-preference-updater`,
    });
    const weeklyBatch = new lambda.Function(this, 'WeeklyReport', {
      ...commonLambdaProps,
      handler: 'src.auth.weekly_report.handler',
      functionName: `yudane-auth-${envName}-weekly-report`,
    });
    tables['preference-vectors'].grantReadWriteData(dailyBatch);
    tables['safeguard-states'].grantReadWriteData(dailyBatch);

    // --- EventBridge cron 2 本（Q3=A）---
    new events.Rule(this, 'DailyRule', {
      ruleName: `yudane-auth-${envName}-daily`,
      // 日次 04:00 JST = 19:00 UTC
      schedule: events.Schedule.cron({ minute: '0', hour: '19' }),
      targets: [new targets.LambdaFunction(dailyBatch)],
    });
    new events.Rule(this, 'WeeklyRule', {
      ruleName: `yudane-auth-${envName}-weekly`,
      // 週次 日曜 22:00 JST = 日曜 13:00 UTC
      schedule: events.Schedule.cron({ minute: '0', hour: '13', weekDay: 'SUN' }),
      targets: [new targets.LambdaFunction(weeklyBatch)],
    });

    // 注: B-01 Cognito トリガーのアタッチと auth API Lambda（profile/user/debt）は
    // platform User Pool 参照 + API Gateway 統合として Code Generation の結線で追加する。

    this.applyNagSuppressions();
  }

  /** cdk-nag の正当な抑制（理由コメント必須）。 */
  private applyNagSuppressions(): void {
    NagSuppressions.addStackSuppressions(this, [
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'Lambda 実行ロールの AWSLambdaBasicExecutionRole は MVP で許容。決勝前にカスタムポリシー化を検討（SECURITY-06）',
      },
      {
        id: 'AwsSolutions-L1',
        reason: 'Python 3.13 は最新ランタイム。L1（最新ランタイム）の誤検出',
      },
    ]);
  }
}
