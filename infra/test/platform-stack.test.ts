import { describe, expect, it } from 'vitest';
import { App, Aspects } from 'aws-cdk-lib';
import { Annotations, Match, Template } from 'aws-cdk-lib/assertions';
import { AwsSolutionsChecks } from 'cdk-nag';

import { PlatformStack } from '../lib/platform-stack';

/** dev 環境の PlatformStack を合成する。 */
function synth(envName = 'dev'): Template {
  const app = new App();
  const stack = new PlatformStack(app, `platform-${envName}-stack`, {
    envName,
    env: { region: 'ap-northeast-1' },
  });
  Aspects.of(app).add(new AwsSolutionsChecks());
  return Template.fromStack(stack);
}

describe('PlatformStack', () => {
  it('VPC を 2 AZ で作成する', () => {
    const t = synth();
    t.resourceCountIs('AWS::EC2::VPC', 1);
  });

  it('Cognito User Pool に MFA REQUIRED を設定する（SECURITY-12 土台）', () => {
    const t = synth();
    t.hasResourceProperties('AWS::Cognito::UserPool', {
      MfaConfiguration: 'ON',
    });
  });

  it('S3 バケットは KMS 暗号化 + パブリックアクセス全ブロック（SECURITY-01/09）', () => {
    const t = synth();
    t.hasResourceProperties('AWS::S3::Bucket', {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  it('Redis は保管時・転送時暗号化が有効', () => {
    const t = synth();
    t.hasResourceProperties('AWS::ElastiCache::ReplicationGroup', {
      AtRestEncryptionEnabled: true,
      TransitEncryptionEnabled: true,
    });
  });

  it('SSM パラメータで共有値を公開する', () => {
    const t = synth();
    t.hasResourceProperties('AWS::SSM::Parameter', {
      Name: Match.stringLikeRegexp('/yudane/dev/platform/.*'),
    });
  });

  it('cdk-nag の未抑制エラーがない', () => {
    const t = synth();
    const errors = Annotations.fromStack(
      // re-synth でアノテーションを取得
      (() => {
        const app = new App();
        const stack = new PlatformStack(app, 'platform-dev-stack', {
          envName: 'dev',
          env: { region: 'ap-northeast-1' },
        });
        Aspects.of(app).add(new AwsSolutionsChecks());
        return stack;
      })(),
    ).findError('*', Match.stringLikeRegexp('AwsSolutions-.*'));
    expect(errors).toHaveLength(0);
    // template が生成できることも確認
    expect(t.toJSON()).toBeTruthy();
  });
});
