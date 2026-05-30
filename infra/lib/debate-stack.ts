/**
 * DebateStack — Unit-3 Debate（infrastructure-design.md）。
 *
 * AgentCore Runtime + Memory + Bedrock Guardrails + DynamoDB Cooldowns + SSM 6 個。
 * platform-stack の SSM 出力（KMS Key / SNS Topic / UserPool / UserPoolClient）を参照する。
 *
 * Phase 1 では AgentCore Runtime / Memory / RuntimeEndpoint を CDK L2（Runtime / Memory /
 * RuntimeEndpoint）で実装する。L2 が将来 break する場合に備え、Phase 1 Plan §7 リスク 1 に
 * 沿って L1（Cfn*）フォールバックの選択肢を残す。Bedrock 関連 IAM 許可は最小権限 + ARN
 * ワイルドカード Suppression（model-id 切替時の AccessDenied 防止）。
 *
 * 参照: aidlc-docs/construction/unit-3-debate/infrastructure-design/infrastructure-design.md
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md
 */

import * as path from 'node:path';

import {
  aws_bedrock as bedrock,
  aws_bedrockagentcore as agentcore,
  aws_cognito as cognito,
  aws_dynamodb as dynamodb,
  aws_glue as glue,
  aws_iam as iam,
  aws_kms as kms,
  aws_s3 as s3,
  aws_sns as sns,
  aws_ssm as ssm,
  Duration,
  RemovalPolicy,
  Stack,
  type StackProps,
} from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import type { Construct } from 'constructs';

/** DebateStack のプロパティ。 */
export interface DebateStackProps extends StackProps {
  /** 環境名（dev / prd）。removalPolicy を切り替える。 */
  envName: string;
}

/**
 * Unit-3 Debate のスタック。AgentCore Runtime + Memory + Bedrock Guardrail +
 * Cooldowns DDB + SSM 6 個（Phase 1 範囲）を構築する。
 */
export class DebateStack extends Stack {
  constructor(scope: Construct, id: string, props: DebateStackProps) {
    super(scope, id, props);

    const { envName } = props;
    const isProd = envName === 'prd';
    const removalPolicy = isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    // === Unit-1 platform-stack の SSM 出力を参照（CDK synth 時に解決）===
    // Export/Import を避け SSM Parameter Store 経由で連携（tech-cdk §3）
    const kmsKeyArn = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/kms-key-arn`,
    );
    const alertsTopicArn = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/alerts-topic-arn`,
    );
    const userPoolId = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/userpool-id`,
    );
    const userPoolClientId = ssm.StringParameter.valueForStringParameter(
      this,
      `/yudane/${envName}/platform/userpool-client-id`,
    );

    // 復元（IKey / Topic / IUserPool 型へ、infrastructure-design §1.3 IAM / Authorizer 用に必要）
    const platformKey = kms.Key.fromKeyArn(this, 'PlatformKey', kmsKeyArn);
    // SNS Topic は Phase 6 Alarm 設定で使用（Phase 1 では Construct 化のみ、後続 Phase で参照）
    const alertsTopic = sns.Topic.fromTopicArn(this, 'AlertsTopic', alertsTopicArn);
    void alertsTopic;

    const userPool = cognito.UserPool.fromUserPoolId(this, 'PlatformUserPool', userPoolId);
    const userPoolClient = cognito.UserPoolClient.fromUserPoolClientId(
      this,
      'PlatformUserPoolClient',
      userPoolClientId,
    );

    // === Cooldowns DDB（Q2=C 唯一の自前テーブル）===
    const cooldownsTable = new dynamodb.Table(this, 'CooldownsTable', {
      tableName: `yudane-debate-${envName}-cooldowns`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: platformKey,
      timeToLiveAttribute: 'ttl',
      removalPolicy,
    });

    // === Bedrock Guardrails（NG-1〜8 = 8 DENIED_TOPICS、Q12=D 第 2 層）===
    const guardrail = new bedrock.CfnGuardrail(this, 'DebateGuardrail', {
      name: `yudane-debate-${envName}-guardrail`,
      description: 'YUDANE Unit-3 NG-1〜8 検出、特に NG-6（脅迫・罪悪感強要）滑落防止',
      blockedInputMessaging: '入力に NG-1〜8 該当の表現が含まれます',
      blockedOutputsMessaging: 'AI が言葉を選び直しています',
      topicPolicyConfig: {
        topicsConfig: [
          {
            name: 'illegal-activity',
            type: 'DENY',
            definition: 'NG-1: 違法行為（不法薬物 / 武器 / 詐欺 等）の助長',
          },
          {
            name: 'health-harm',
            type: 'DENY',
            definition: 'NG-2: 健康被害（過度な飲酒 / 過食 / 自己破壊行動）の誘導',
          },
          {
            name: 'discrimination',
            type: 'DENY',
            definition: 'NG-3: 性別 / 人種 / 宗教 / 障がいに基づく差別表現',
          },
          {
            name: 'minor-targeting',
            type: 'DENY',
            definition: 'NG-4: 未成年者を直接の対象とする論破 / 購買誘導',
          },
          {
            name: 'mental-health',
            type: 'DENY',
            definition: 'NG-5: 精神衛生上の害（自傷示唆 / 希死念慮 等）への接続',
          },
          {
            name: 'threat-or-guilt-coercion',
            type: 'DENY',
            definition: 'NG-6 最重要: 脅迫 / 罪悪感の強要 / 人格否定による購買強制',
          },
          {
            name: 'personal-data-misuse',
            type: 'DENY',
            definition: 'NG-7: 個人データの不正利用 / 不当開示',
          },
          {
            name: 'associates-violation',
            type: 'DENY',
            definition: 'NG-8: Amazon Associates Operating Agreement 違反コピー',
          },
        ],
      },
      contentPolicyConfig: {
        filtersConfig: [
          { type: 'HATE', inputStrength: 'HIGH', outputStrength: 'HIGH' },
          { type: 'VIOLENCE', inputStrength: 'HIGH', outputStrength: 'HIGH' },
          { type: 'SEXUAL', inputStrength: 'HIGH', outputStrength: 'HIGH' },
          { type: 'INSULTS', inputStrength: 'HIGH', outputStrength: 'HIGH' },
        ],
      },
    });

    // === AgentCore Memory（Q1=C / Q10=B、組み込み 2 + Phase 4 で custom 1 を追加）===
    const memory = new agentcore.Memory(this, 'DebateMemory', {
      memoryName: `yudane_debate_${envName}_memory`, // a-zA-Z0-9_ のみ
      description: 'YUDANE Unit-3 Debate Memory: events + 2 builtin + 1 custom strategies',
      expirationDuration: Duration.days(90), // business-rules MEMORY-02
      kmsKey: platformKey,
      memoryStrategies: [
        // P0: userPreference 組み込み（debate_outcomes）
        agentcore.MemoryStrategy.usingUserPreference({
          strategyName: 'debate_outcomes',
          description: 'ユーザーが翻意した軸 / ターン数 / 商品カテゴリの好みを保存',
          namespaces: ['/user/debate/{actorId}/'],
        }),
        // P0: semantic 組み込み（stress_signals）
        agentcore.MemoryStrategy.usingSemantic({
          strategyName: 'stress_signals',
          description: '直近の活動パターンからストレス兆候を抽出',
          namespaces: ['/user/stress/{actorId}/'],
        }),
        // P1: custom Strategy `m1_m2_axis_extractor`（Phase 4 Step 4-2）。
        // L2 SelfManaged は SNS+S3 必須で重いため、L1 CustomMemoryStrategy を
        // CfnMemory.addPropertyOverride で末尾に追加する（後段で実装）。
      ],
    });

    // Phase 4 Step 4-2: custom Memory Strategy `m1_m2_axis_extractor` を L1 直書きで追加。
    // M-1 / M-2 軸の翻意パターンを Bedrock Haiku 4.5 で抽出 →
    // /user/m1m2/{actorId}/ namespace に保存（B-303 採用済、prompts/m1_m2_axis_extractor.py と整合）。
    // L2 が CustomMemoryStrategy をネイティブサポートしたら本ブロックを差し替える。
    // L2 Memory は内部で id='Memory' の CfnMemory を生成する（aws-cdk-lib v2.257+ 実装に基づく）。
    const cfnMemory = memory.node.findChild('Memory') as agentcore.CfnMemory;
    cfnMemory.addPropertyOverride('MemoryStrategies.2', {
      CustomMemoryStrategy: {
        Name: 'm1_m2_axis_extractor',
        Description:
          'M-1 / M-2 軸の翻意パターンを Haiku 4.5 で構造化抽出（FACT / PSYCHOLOGY / REWARD）',
        Namespaces: ['/user/m1m2/{actorId}/'],
      },
    });

    // === AgentCore Runtime IAM Role（最小権限）===
    const runtimeRole = new iam.Role(this, 'DebateRuntimeRole', {
      roleName: `yudane-debate-${envName}-runtime-role`,
      assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
      description: 'YUDANE Unit-3 AgentCore Runtime 実行ロール',
    });

    // Bedrock 2 ARN ワイルドカード（Haiku 4.5 + Sonnet 4.6 先行付与）
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: [
          `arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-haiku-4-5*`,
          `arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-sonnet-4-6*`,
        ],
      }),
    );

    // AgentCore Memory のイベント書き込み + 取得（namespace は actor_id 単位、コードで強制）
    // 注: actor_id 単位の分離は IAM では不可能（単一 Runtime IAM Role が全ユーザーの Memory に
    //     アクセスする設計）。実際の actor_id 単位分離は Strands Agent コード内の
    //     `f'/user/.../{actor_id}/'` を必ず付与し、CI Lint で `{actor_id}` を抜いた汎用
    //     namespace を fail させる（PAT-D-SEC-02 / NFR-SEC-DEBATE-04 と整合）。
    memory.grantWrite(runtimeRole);
    memory.grantRead(runtimeRole);

    // DDB Cooldowns
    cooldownsTable.grantReadWriteData(runtimeRole);

    // KMS（DDB / Memory / Logs 暗号化に必要）
    platformKey.grantEncryptDecrypt(runtimeRole);

    // Bedrock Guardrail を Runtime からの InvokeModel 呼び出しに紐付ける権限
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:ApplyGuardrail'],
        resources: [guardrail.attrGuardrailArn],
      }),
    );

    // SSM（model-id / kill-switch を Strands Agent が読み取る）
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter'],
        resources: [
          this.formatArn({
            service: 'ssm',
            resource: 'parameter',
            resourceName: `yudane/${envName}/debate/model-id`,
          }),
          this.formatArn({
            service: 'ssm',
            resource: 'parameter',
            resourceName: `yudane/${envName}/debate/kill-switch`,
          }),
        ],
      }),
    );

    // CloudWatch Logs / Metrics（EMF）+ X-Ray（NFR-OBS-DEBATE-10）
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'logs:CreateLogStream',
          'logs:PutLogEvents',
          'logs:CreateLogGroup',
          'cloudwatch:PutMetricData',
          'xray:PutTraceSegments',
          'xray:PutTelemetryRecords',
        ],
        // 注: cloudwatch:PutMetricData / xray:* は AWS の制約上 Resource: '*' が必須。
        //     ネームスペース絞り込みは EMF Dimensions 側で yudane.debate に統一する
        //     （PAT-D-OBS-02、infrastructure-design §6.2）。
        resources: ['*'],
      }),
    );

    // === AgentCore Runtime（Direct Code Deploy + Cognito Authorizer + Public Network）===
    // Phase 1 では backend/src/debate を S3 zip として bundle してデプロイ。
    // Phase 2 で requirements.txt の依存解決を bundling で実施（task-breakdown Phase 2 T2.1）。
    const runtimeArtifact = agentcore.AgentRuntimeArtifact.fromCodeAsset({
      path: path.join(__dirname, '..', '..', 'backend', 'src', 'debate'),
      runtime: agentcore.AgentCoreRuntime.PYTHON_3_13,
      entrypoint: ['main.py'],
    });

    const runtime = new agentcore.Runtime(this, 'DebateRuntime', {
      runtimeName: `yudane_debate_${envName}`,
      description: 'YUDANE Unit-3 Debate Strands Agent runtime',
      executionRole: runtimeRole,
      agentRuntimeArtifact: runtimeArtifact,
      // Q6=A、Public Network（VPC 配置なし、ENI コールドスタート回避、SECURITY-07 例外）
      networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingPublicNetwork(),
      // Cognito Authorizer は Unit-1 platform-stack の User Pool を再利用
      authorizerConfiguration: agentcore.RuntimeAuthorizerConfiguration.usingCognito(
        userPool,
        [userPoolClient],
      ),
      environmentVariables: {
        ENV_NAME: envName,
        DEBATE_MEMORY_ID: memory.memoryId,
        BEDROCK_GUARDRAIL_ID: guardrail.attrGuardrailId,
        COOLDOWNS_TABLE_NAME: cooldownsTable.tableName,
      },
      // タイマー二段の物理層（PAT-D-PERF-02、business-rules カタログ §12）。
      // Strands Agent 90s 厳守の保険として +30s バッファ、microVM 強制終了は 120s。
      lifecycleConfiguration: {
        idleRuntimeSessionTimeout: Duration.seconds(120),
        maxLifetime: Duration.seconds(120),
      },
      // X-Ray トレース有効化（NFR-OBS-DEBATE-10）
      tracingEnabled: true,
    });

    // === RuntimeEndpoint live（canary は Phase 5 で追加）===
    const liveEndpoint = new agentcore.RuntimeEndpoint(this, 'DebateRuntimeLive', {
      agentRuntimeId: runtime.agentRuntimeId,
      endpointName: 'live',
      description: 'YUDANE Debate live endpoint（通常運用）',
    });

    // === SSM 出力（Phase 1 = 6 個 + Phase 3-3 で memory-export-bucket-arn を追加 = 7 個。Phase 5 で +runtime-endpoint-canary-arn）===
    this.publishParam('runtime-arn', runtime.agentRuntimeArn, envName);
    this.publishParam('memory-id', memory.memoryId, envName);
    this.publishParam('runtime-endpoint-live-arn', liveEndpoint.agentRuntimeEndpointArn, envName);
    this.publishParam('cooldowns-table-arn', cooldownsTable.tableArn, envName);
    // model-id は SSM 既定値で初期化（Phase 1 から Strands Agent が起動時 GetParameter で取得、
    // Bedrock モデル切替時はこの SSM 値を put-parameter で更新後、Runtime をローリング再起動）
    this.publishParam('model-id', 'anthropic.claude-haiku-4-5', envName);
    // kill-switch は既定 disabled（緊急時のみ enabled に切替、PAT-D-COST-04）
    this.publishParam('kill-switch', 'disabled', envName);

    // === Phase 3-3: S3 Memory Export Bucket + Glue Crawler（CDK Snapshot のみ、実 deploy なし）===
    // Memory `streamDeliveryResources` の S3 直結は CFN 仕様上 Kinesis 経由のみサポート。
    // 本 Phase では Bucket + Glue + IAM + 7 個目 SSM の整備のみ実施し、Memory ↔ S3 の
    // データ流入経路は B-308 backlog 化（Kinesis Firehose 連鎖実装）。
    // 参照: doc/backlog.md B-308
    const memoryExportBucket = new s3.Bucket(this, 'MemoryExportBucket', {
      bucketName: `yudane-debate-${envName}-memory-export`,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: platformKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      enforceSSL: true,
      lifecycleRules: [
        {
          id: 'memory-export-tiering',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: Duration.days(90),
            },
          ],
          expiration: Duration.days(365),
        },
      ],
      removalPolicy,
      autoDeleteObjects: !isProd, // dev のみ自動削除許容、prd は明示的承認後に削除
    });

    // cdk-nag suppression: MemoryExportBucket は Memory イベントの export 先
    // server access logs は決勝後の運用フェーズで導入検討（B-308 backlog の一部）。
    // 決勝までは KMS + BlockPublicAccess + Lifecycle で機密性 / コストを担保
    NagSuppressions.addResourceSuppressions(
      memoryExportBucket,
      [
        {
          id: 'AwsSolutions-S1',
          reason:
            'Server access logs は決勝後の運用フェーズで導入。MVP では KMS / BlockPublicAccess / enforceSSL / Lifecycle 30/90/365d で機密性確保（B-308 backlog で対応）',
        },
      ],
      true,
    );

    // Glue Database（MemoryExport 用、Athena で query 可能）
    const glueDatabase = new glue.CfnDatabase(this, 'MemoryExportDatabase', {
      catalogId: this.account,
      databaseInput: {
        name: `yudane_debate_${envName}_memory_export`,
        description: 'YUDANE Unit-3 Memory Export Athena database',
      },
    });

    // Glue Crawler 実行ロール（Glue → S3 + KMS）
    const memoryExportCrawlerRole = new iam.Role(this, 'MemoryExportCrawlerRole', {
      roleName: `yudane-debate-${envName}-memory-export-crawler-role`,
      assumedBy: new iam.ServicePrincipal('glue.amazonaws.com'),
      description: 'YUDANE Unit-3 Memory Export Glue Crawler 実行ロール',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'),
      ],
    });
    memoryExportBucket.grantRead(memoryExportCrawlerRole);
    platformKey.grantDecrypt(memoryExportCrawlerRole);

    // Glue Crawler（cron 1:00 UTC daily）
    const memoryExportCrawler = new glue.CfnCrawler(this, 'MemoryExportCrawler', {
      name: `yudane-debate-${envName}-memory-export-crawler`,
      role: memoryExportCrawlerRole.roleArn,
      databaseName: `yudane_debate_${envName}_memory_export`,
      targets: {
        s3Targets: [
          {
            path: `s3://${memoryExportBucket.bucketName}/`,
          },
        ],
      },
      schedule: {
        scheduleExpression: 'cron(0 1 * * ? *)',
      },
      schemaChangePolicy: {
        updateBehavior: 'UPDATE_IN_DATABASE',
        deleteBehavior: 'LOG',
      },
    });
    // Crawler は Database に依存（同一 stack で先後関係を明示）
    memoryExportCrawler.node.addDependency(glueDatabase);

    // Phase 3-3 で 7 個目の SSM を出力（B-308 で Kinesis Firehose チェーン実装時に Memory が参照）
    this.publishParam('memory-export-bucket-arn', memoryExportBucket.bucketArn, envName);

    this.applyNagSuppressions(runtimeRole);
  }

  /** SSM Parameter として共有値を公開する。 */
  private publishParam(key: string, value: string, envName: string): void {
    new ssm.StringParameter(this, `Param-${key}`, {
      parameterName: `/yudane/${envName}/debate/${key}`,
      stringValue: value,
    });
  }

  /** cdk-nag の正当な抑制（理由コメント必須、tech-cdk §2）。 */
  private applyNagSuppressions(runtimeRole: iam.Role): void {
    NagSuppressions.addStackSuppressions(this, [
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'CDK が DDB / Memory の自動生成リソースに付与する AWS 管理ポリシー。MVP では許容、決勝前にカスタムポリシー化を検討（NFR-SEC SECURITY-06）',
      },
      {
        id: 'AwsSolutions-IAM5',
        reason:
          'Memory grantWrite/grantRead と DDB grantReadWriteData が actor_id ごとの絞り込みなしで付与される。actor_id 単位の分離は Strands Agent コード内 namespace + CI Lint で強制（PAT-D-SEC-02）',
      },
    ]);
    NagSuppressions.addResourceSuppressions(
      runtimeRole,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason:
            'Bedrock 2 ARN ワイルドカード（claude-haiku-4-5* / claude-sonnet-4-6*）は SSM 経由のモデル切替時に AccessDenied を起こさないため必要（infrastructure-design §1.3）。logs/cloudwatch/xray の Resource:* は AWS 制約上必須、ネームスペース絞り込みは EMF Dimensions で yudane.debate に統一（PAT-D-OBS-02）',
        },
      ],
      true,
    );
  }
}
