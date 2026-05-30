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

import { AuthStack } from '../lib/auth-stack';
import { CartStack } from '../lib/cart-stack';
import { PlatformStack } from '../lib/platform-stack';
import { ReelStack } from '../lib/reel-stack';

const app = new App();

const env = (app.node.tryGetContext('env') as string | undefined) ?? 'dev';
const region = (app.node.tryGetContext('region') as string | undefined) ?? 'ap-northeast-1';
const developerInitial = app.node.tryGetContext('developer') as string | undefined;

const stackSuffix = developerInitial && env === 'dev' ? `-${developerInitial}` : '';

new PlatformStack(app, `platform-${env}${stackSuffix}-stack`, {
  envName: env,
  env: { region },
});

// Unit-2 Auth & Profile
new AuthStack(app, `auth-${env}-stack`, {
  envName: env,
  env: { region },
});

// Unit-4 Reel（platform-stack の後段にデプロイ、SSM 参照で連携）
new ReelStack(app, `reel-${env}-stack`, {
  envName: env,
  env: { region },
});

// Unit-5 Cart Intercept（infrastructure-design.md / cart-stack.ts 整合）
// exactOptionalPropertyTypes: true のため、developerInitial が undefined のときは
// プロパティ自体を省略する（spread で条件付きマージ）
new CartStack(app, `cart-${env}${stackSuffix}-stack`, {
  envName: env as 'dev' | 'prd',
  ...(developerInitial !== undefined ? { developerInitial } : {}),
  // platformKmsKey: 未指定（PlatformStack 整備中のため Stack 内 fallback、Member A 整備後に切替）
  env: { region },
});

// cdk-nag を全スタックに適用（無言サプレッション禁止）
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
