/**
 * DebateStack Snapshot TDD（Phase 1 Step 1.1 Red）。
 *
 * 参照: aidlc-docs/construction/plans/unit-3-debate-code-generation-phase1-plan.md §1 Step 1
 * 参照: aidlc-docs/construction/unit-3-debate/infrastructure-design/infrastructure-design.md
 *
 * 注: AgentCore Runtime / Memory は CDK L1（CfnRuntime / CfnMemory）で実装する
 *     （Phase 1 Plan §7 リスク 1 のフォールバック方針に従う）。
 */

import { App, Aspects } from 'aws-cdk-lib';
import { Annotations, Match, Template } from 'aws-cdk-lib/assertions';
import { AwsSolutionsChecks } from 'cdk-nag';
import { describe, expect, it } from 'vitest';

import { DebateStack } from '../lib/debate-stack';

/** dev 環境の DebateStack を合成する。 */
function synth(envName = 'dev'): Template {
  const app = new App();
  const stack = new DebateStack(app, `debate-${envName}-stack`, {
    envName,
    env: { region: 'ap-northeast-1' },
  });
  Aspects.of(app).add(new AwsSolutionsChecks());
  return Template.fromStack(stack);
}

describe('DebateStack', () => {
  it('AgentCore Runtime を 1 個含む（Direct Code Deploy + Cognito Authorizer + Public Network）', () => {
    const t = synth();
    t.resourceCountIs('AWS::BedrockAgentCore::Runtime', 1);
    t.hasResourceProperties('AWS::BedrockAgentCore::Runtime', {
      AgentRuntimeName: 'yudane_debate_dev',
      NetworkConfiguration: { NetworkMode: 'PUBLIC' },
    });
  });

  it('AgentCore RuntimeEndpoint live を 1 個定義する（canary は P1）', () => {
    const t = synth();
    t.resourceCountIs('AWS::BedrockAgentCore::RuntimeEndpoint', 1);
    t.hasResourceProperties('AWS::BedrockAgentCore::RuntimeEndpoint', {
      Name: 'live',
    });
  });

  it('AgentCore Memory を 1 個含み expirationDuration 90 日 + 組み込み 2 Strategy', () => {
    const t = synth();
    t.resourceCountIs('AWS::BedrockAgentCore::Memory', 1);
    t.hasResourceProperties('AWS::BedrockAgentCore::Memory', {
      Name: 'yudane_debate_dev_memory',
      EventExpiryDuration: 90,
      MemoryStrategies: Match.arrayWith([
        Match.objectLike({
          UserPreferenceMemoryStrategy: Match.objectLike({
            Name: 'debate_outcomes',
          }),
        }),
        Match.objectLike({
          SemanticMemoryStrategy: Match.objectLike({
            Name: 'stress_signals',
          }),
        }),
      ]),
    });
  });

  // Phase 4 Step 4-2: custom Memory Strategy `m1_m2_axis_extractor`（CDK Snapshot のみ）
  it('Memory が CustomMemoryStrategy m1_m2_axis_extractor を含む', () => {
    const t = synth();
    t.hasResourceProperties('AWS::BedrockAgentCore::Memory', {
      MemoryStrategies: Match.arrayWith([
        Match.objectLike({
          CustomMemoryStrategy: Match.objectLike({
            Name: 'm1_m2_axis_extractor',
            Namespaces: ['/user/m1m2/{actorId}/'],
          }),
        }),
      ]),
    });
  });

  it('DDB CooldownsTable は PAY_PER_REQUEST + KMS + PITR + TTL=ttl', () => {
    const t = synth();
    t.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'yudane-debate-dev-cooldowns',
      BillingMode: 'PAY_PER_REQUEST',
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
      TimeToLiveSpecification: { AttributeName: 'ttl', Enabled: true },
      SSESpecification: Match.objectLike({ SSEEnabled: true }),
    });
  });

  it('Bedrock Guardrail に NG-1〜8 の 8 DENIED_TOPICS を含む', () => {
    const t = synth();
    t.hasResourceProperties('AWS::Bedrock::Guardrail', {
      Name: 'yudane-debate-dev-guardrail',
      TopicPolicyConfig: Match.objectLike({
        TopicsConfig: Match.arrayWith([
          Match.objectLike({ Name: 'illegal-activity', Type: 'DENY' }),
          Match.objectLike({ Name: 'health-harm', Type: 'DENY' }),
          Match.objectLike({ Name: 'discrimination', Type: 'DENY' }),
          Match.objectLike({ Name: 'minor-targeting', Type: 'DENY' }),
          Match.objectLike({ Name: 'mental-health', Type: 'DENY' }),
          Match.objectLike({ Name: 'threat-or-guilt-coercion', Type: 'DENY' }),
          Match.objectLike({ Name: 'personal-data-misuse', Type: 'DENY' }),
          Match.objectLike({ Name: 'associates-violation', Type: 'DENY' }),
        ]),
      }),
    });
  });

  it('IAM Role が Bedrock 2 ARN ワイルドカード（Haiku 4.5 + Sonnet 4.6 先行付与）を持つ', () => {
    const t = synth();
    // Runtime 実行ロールに Bedrock InvokeModel ポリシーが付与されていることを確認
    t.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: Match.arrayWith([
              'bedrock:InvokeModel',
              'bedrock:InvokeModelWithResponseStream',
            ]),
            Resource: Match.arrayWith([
              Match.stringLikeRegexp('.*claude-haiku-4-5.*'),
              Match.stringLikeRegexp('.*claude-sonnet-4-6.*'),
            ]),
          }),
        ]),
      }),
    });
  });

  it('SSM Parameter を 7 個出力する（Phase 1 = 6 個 + Phase 3-3 で +memory-export-bucket-arn）', () => {
    const t = synth();
    const params = t.findResources('AWS::SSM::Parameter');
    const names = Object.values(params).map((r) => r.Properties.Name as string);
    // Phase 1 (6 個) + Phase 3-3 で memory-export-bucket-arn を追加
    const expected = [
      '/yudane/dev/debate/runtime-arn',
      '/yudane/dev/debate/memory-id',
      '/yudane/dev/debate/runtime-endpoint-live-arn',
      '/yudane/dev/debate/model-id',
      '/yudane/dev/debate/cooldowns-table-arn',
      '/yudane/dev/debate/kill-switch',
      '/yudane/dev/debate/memory-export-bucket-arn',
    ];
    for (const name of expected) {
      expect(names).toContain(name);
    }
    expect(names).toHaveLength(7);
  });

  // Phase 3 Step 3-3: Memory Export Bucket + Glue Crawler（CDK Snapshot のみ、実 deploy なし）
  it('S3 Memory Export Bucket は KMS + BlockPublicAccess + Lifecycle 30/90/365 日 + Versioned', () => {
    const t = synth();
    t.hasResourceProperties('AWS::S3::Bucket', {
      BucketName: 'yudane-debate-dev-memory-export',
      BucketEncryption: Match.objectLike({
        ServerSideEncryptionConfiguration: Match.arrayWith([
          Match.objectLike({
            ServerSideEncryptionByDefault: Match.objectLike({
              SSEAlgorithm: 'aws:kms',
            }),
          }),
        ]),
      }),
      PublicAccessBlockConfiguration: Match.objectLike({
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      }),
      VersioningConfiguration: Match.objectLike({ Status: 'Enabled' }),
      LifecycleConfiguration: Match.objectLike({
        Rules: Match.arrayWith([
          Match.objectLike({
            Status: 'Enabled',
            Transitions: Match.arrayWith([
              Match.objectLike({
                StorageClass: 'STANDARD_IA',
                TransitionInDays: 30,
              }),
              Match.objectLike({
                StorageClass: 'GLACIER',
                TransitionInDays: 90,
              }),
            ]),
            ExpirationInDays: 365,
          }),
        ]),
      }),
    });
  });

  it('Glue Crawler が cron(0 1 * * ? *) で MemoryExportBucket をスキャンする', () => {
    const t = synth();
    t.resourceCountIs('AWS::Glue::Database', 1);
    t.hasResourceProperties('AWS::Glue::Database', {
      DatabaseInput: Match.objectLike({
        Name: 'yudane_debate_dev_memory_export',
      }),
    });
    t.resourceCountIs('AWS::Glue::Crawler', 1);
    t.hasResourceProperties('AWS::Glue::Crawler', {
      Name: 'yudane-debate-dev-memory-export-crawler',
      Schedule: Match.objectLike({
        ScheduleExpression: 'cron(0 1 * * ? *)',
      }),
      DatabaseName: 'yudane_debate_dev_memory_export',
    });
  });

  it('Memory Export 用 IAM Role が S3 PutObject + KMS Encrypt 権限を持つ', () => {
    const t = synth();
    // Glue Crawler 実行ロール（Glue → S3 + KMS）
    t.hasResourceProperties('AWS::IAM::Role', {
      AssumeRolePolicyDocument: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Principal: Match.objectLike({
              Service: 'glue.amazonaws.com',
            }),
          }),
        ]),
      }),
    });
  });

  it('cdk-nag の未抑制エラーがない', () => {
    // 単独で再合成してアノテーションを取得
    const app = new App();
    const stack = new DebateStack(app, 'debate-dev-stack', {
      envName: 'dev',
      env: { region: 'ap-northeast-1' },
    });
    Aspects.of(app).add(new AwsSolutionsChecks());
    const errors = Annotations.fromStack(stack).findError(
      '*',
      Match.stringLikeRegexp('AwsSolutions-.*'),
    );
    expect(errors).toHaveLength(0);
  });

  it('CloudFormation テンプレートのスナップショットを固定する（Snapshot fixture）', () => {
    const t = synth();
    expect(t.toJSON()).toMatchSnapshot();
  });
});
