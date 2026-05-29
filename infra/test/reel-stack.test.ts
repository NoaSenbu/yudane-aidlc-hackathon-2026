import { describe, expect, it } from 'vitest';
import { App, Aspects } from 'aws-cdk-lib';
import { Annotations, Match, Template } from 'aws-cdk-lib/assertions';
import { AwsSolutionsChecks } from 'cdk-nag';

import { ReelStack } from '../lib/reel-stack';

/** dev 環境の ReelStack を合成する。 */
function synth(envName = 'dev'): Template {
  const app = new App();
  const stack = new ReelStack(app, `reel-${envName}-stack`, {
    envName,
    env: { region: 'ap-northeast-1' },
  });
  Aspects.of(app).add(new AwsSolutionsChecks());
  return Template.fromStack(stack);
}

describe('ReelStack', () => {
  it('amazon-transitions テーブルを On-Demand + KMS + PITR + TTL で作成する（Q2=A）', () => {
    const t = synth();
    t.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'yudane-reel-dev-amazon-transitions',
      BillingMode: 'PAY_PER_REQUEST',
      TimeToLiveSpecification: { AttributeName: 'ttl', Enabled: true },
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
    });
  });

  it('amazon-transitions に gsi-month を持つ（北極星集計）', () => {
    const t = synth();
    t.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'yudane-reel-dev-amazon-transitions',
      GlobalSecondaryIndexes: Match.arrayWith([
        Match.objectLike({ IndexName: 'gsi-month' }),
      ]),
    });
  });

  it('impressions テーブルを作成する', () => {
    const t = synth();
    t.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'yudane-reel-dev-impressions',
      BillingMode: 'PAY_PER_REQUEST',
    });
  });

  it('feed / transition Lambda を Python 3.13 + ARM64 で作成する', () => {
    const t = synth();
    t.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'yudane-reel-dev-feed',
      Runtime: 'python3.13',
      Architectures: ['arm64'],
    });
    t.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'yudane-reel-dev-transition',
      Runtime: 'python3.13',
    });
  });

  it('Lambda Alias（live）を持つ（SnapStart 運用）', () => {
    const t = synth();
    t.resourceCountIs('AWS::Lambda::Alias', 2);
  });

  it('reel 固有 SSM パラメータを公開する', () => {
    const t = synth();
    t.hasResourceProperties('AWS::SSM::Parameter', {
      Name: Match.stringLikeRegexp('/yudane/dev/reel/.*'),
    });
  });

  it('usage plan（429 レート制限）を持つ（SECURITY-11）', () => {
    const t = synth();
    t.resourceCountIs('AWS::ApiGateway::UsagePlan', 1);
  });

  it('cdk-nag の未抑制エラーがない', () => {
    const app = new App();
    const stack = new ReelStack(app, 'reel-dev-stack', {
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
});
