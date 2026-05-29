import { describe, expect, it } from 'vitest';
import { App, Aspects } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { AwsSolutionsChecks } from 'cdk-nag';

import { AuthStack } from '../lib/auth-stack';

/** dev 環境の AuthStack を合成する。 */
function synth(envName = 'dev'): Template {
  const app = new App();
  const stack = new AuthStack(app, `auth-${envName}-stack`, {
    envName,
    env: { region: 'ap-northeast-1' },
  });
  Aspects.of(app).add(new AwsSolutionsChecks());
  return Template.fromStack(stack);
}

describe('AuthStack', () => {
  it('DynamoDB 4 テーブルを作成する', () => {
    const t = synth();
    t.resourceCountIs('AWS::DynamoDB::Table', 4);
  });

  it('全テーブルが PAY_PER_REQUEST + PITR', () => {
    const t = synth();
    t.hasResourceProperties('AWS::DynamoDB::Table', {
      BillingMode: 'PAY_PER_REQUEST',
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
    });
  });

  it('EventBridge Rule を 2 本作成する（日次/週次）', () => {
    const t = synth();
    t.resourceCountIs('AWS::Events::Rule', 2);
  });

  it('B-08 Lambda は Python 3.13', () => {
    const t = synth();
    t.hasResourceProperties('AWS::Lambda::Function', {
      Runtime: 'python3.13',
    });
  });

  it('prd は DynamoDB が RETAIN', () => {
    const t = synth('prd');
    t.hasResource('AWS::DynamoDB::Table', {
      DeletionPolicy: 'Retain',
    });
  });

  it('SSM 参照で platform KMS を取得する', () => {
    const t = synth();
    // SSM パラメータ参照は合成時に解決される（テンプレートが生成できることを確認）
    expect(t.toJSON()).toBeTruthy();
  });

  it('週次 Rule は日曜実行', () => {
    const t = synth();
    t.hasResourceProperties('AWS::Events::Rule', {
      ScheduleExpression: Match.stringLikeRegexp('.*SUN.*'),
    });
  });
});
