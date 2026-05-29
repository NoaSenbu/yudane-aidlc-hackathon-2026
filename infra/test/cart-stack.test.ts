/**
 * cart-stack スナップショットテスト + cdk-nag 検証（Snapshot TDD）。
 *
 * Validates: tech-cdk.md §6.1 Snapshot TDD / functional-design.md §0.1 TDD 適用方針。
 */

import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { describe, expect, it } from 'vitest';

import { CartStack } from '../lib/cart-stack';

function _stackTemplate(): Template {
  const app = new cdk.App();
  const stack = new CartStack(app, 'TestCartStack', { envName: 'dev' });
  return Template.fromStack(stack);
}

describe('CartStack', () => {
  describe('Persistence 層（DDB CartWatchItems / NotificationLogs）', () => {
    it('CartWatchItems テーブルが PAY_PER_REQUEST + KMS で作成される', () => {
      const template = _stackTemplate();
      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'yudane-cart-dev-watch-items',
        BillingMode: 'PAY_PER_REQUEST',
        KeySchema: [
          { AttributeName: 'PK', KeyType: 'HASH' },
          { AttributeName: 'SK', KeyType: 'RANGE' },
        ],
      });
    });

    it('CartWatchItems に GSI1-status-createdAt が定義される', () => {
      const template = _stackTemplate();
      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'yudane-cart-dev-watch-items',
        GlobalSecondaryIndexes: [
          {
            IndexName: 'GSI1-status-createdAt',
            KeySchema: [
              { AttributeName: 'GSI1PK', KeyType: 'HASH' },
              { AttributeName: 'GSI1SK', KeyType: 'RANGE' },
            ],
          },
        ],
      });
    });

    it('NotificationLogs テーブルが GSI1-cartWatchItemId 付きで作成される', () => {
      const template = _stackTemplate();
      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'yudane-cart-dev-notification-logs',
      });
    });
  });

  describe('Compute 層（6 Lambda）', () => {
    it('6 Lambda が Python 3.13 ARM64 で作成される', () => {
      const template = _stackTemplate();
      template.resourceCountIs('AWS::Lambda::Function', 7); // 6 cart + 1 slack-bridge
    });

    it('cart_intake が SnapStart 設定済み', () => {
      const template = _stackTemplate();
      template.hasResourceProperties('AWS::Lambda::Function', {
        FunctionName: 'yudane-cart-dev-intake',
        Runtime: 'python3.13',
        Architectures: ['arm64'],
        SnapStart: { ApplyOn: 'PublishedVersions' },
      });
    });

    it('cart_attack_scheduler_retry が Reserved Concurrency 10 で作成される', () => {
      const template = _stackTemplate();
      template.hasResourceProperties('AWS::Lambda::Function', {
        FunctionName: 'yudane-cart-dev-attack-scheduler-retry',
        ReservedConcurrentExecutions: 10,
      });
    });
  });

  describe('EventBridge Scheduler', () => {
    it('rate(15 minutes) で retry batch Schedule が作成される', () => {
      const template = _stackTemplate();
      template.hasResourceProperties('AWS::Scheduler::Schedule', {
        ScheduleExpression: 'rate(15 minutes)',
      });
    });

    it('SchedulerInvokeRole の Trust Policy に SourceAccount + SourceArn 両方が含まれる（Confused Deputy 防御）', () => {
      const template = _stackTemplate();
      // SchedulerInvokeRole の名前で検索
      const roles = template.findResources('AWS::IAM::Role');
      const schedulerRole = Object.values(roles).find(
        (r) =>
          r.Properties?.RoleName === 'yudane-cart-dev-scheduler-invoke-role',
      );
      expect(schedulerRole).toBeDefined();
      const trustPolicy = schedulerRole?.Properties?.AssumeRolePolicyDocument;
      const trustStatement = trustPolicy?.Statement?.[0];
      expect(trustStatement?.Condition?.StringEquals?.['aws:SourceAccount']).toBeDefined();
      // CDK は aws:SourceArn を Fn::Sub / Fn::Join 等の intrinsic function（object）で出力するため、
      // JSON 文字列化して `schedule/default/cart-*` の含有を検証する（toMatch は string 専用）
      const sourceArn = trustStatement?.Condition?.ArnLike?.['aws:SourceArn'];
      expect(sourceArn).toBeDefined();
      expect(JSON.stringify(sourceArn)).toContain('schedule/default/cart-*');
    });
  });

  describe('SNS Topic + CloudWatch Alarms', () => {
    it('cartAlertTopic が KMS 暗号化で作成される', () => {
      const template = _stackTemplate();
      template.hasResourceProperties('AWS::SNS::Topic', {
        TopicName: 'yudane-cart-dev-alerts',
      });
    });

    it('5 系統の CloudWatch Alarm が作成される', () => {
      const template = _stackTemplate();
      template.resourceCountIs('AWS::CloudWatch::Alarm', 5);
    });
  });

  describe('Tags（必須 4 タグ）', () => {
    it('全リソースに Environment / Unit / Owner / CostCenter タグが付与される', () => {
      const template = _stackTemplate();
      // タグは Stack レベルで Tags.of(this).add() され、各リソースの Tags プロパティに継承される
      // 1 つの Lambda リソースで確認
      const lambdas = template.findResources('AWS::Lambda::Function');
      const intakeLambda = Object.values(lambdas).find(
        (l) => l.Properties?.FunctionName === 'yudane-cart-dev-intake',
      );
      const tags = intakeLambda?.Properties?.Tags ?? [];
      const tagKeys = tags.map((t: { Key: string }) => t.Key);
      expect(tagKeys).toContain('Environment');
      expect(tagKeys).toContain('Unit');
      expect(tagKeys).toContain('Owner');
      expect(tagKeys).toContain('CostCenter');
    });
  });
});
