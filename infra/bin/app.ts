#!/usr/bin/env node
/**
 * YUDANE CDK アプリのエントリ。
 *
 * env は context（`-c env=dev|prd`）で切替。リージョンは ap-northeast-1 固定。
 * cdk-nag の AwsSolutionsChecks を全スタックに適用する（tech-cdk §2）。
 */

import 'source-map-support/register';

import { App, Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';

import { PlatformStack } from '../lib/platform-stack';
import { ReelStack } from '../lib/reel-stack';

const app = new App();

const env = (app.node.tryGetContext('env') as string | undefined) ?? 'dev';
const region = (app.node.tryGetContext('region') as string | undefined) ?? 'ap-northeast-1';

new PlatformStack(app, `platform-${env}-stack`, {
  envName: env,
  env: { region },
});

// Unit-4 Reel（platform-stack の後段にデプロイ、SSM 参照で連携）
new ReelStack(app, `reel-${env}-stack`, {
  envName: env,
  env: { region },
});

// cdk-nag を全スタックに適用（無言サプレッション禁止）
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
