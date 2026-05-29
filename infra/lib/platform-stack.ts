/**
 * PlatformStack — Unit-1 Platform の共通基盤（infrastructure-design.md）。
 *
 * VPC / API Gateway + Authorizer / Cognito User Pool / KMS / S3 / ElastiCache Redis /
 * 観測（SNS）/ 共通出力（SSM Parameter Store）を構築する。
 * 他 Unit のスタックは本スタックの SSM 出力を参照する（shared-infrastructure.md）。
 */

import {
  aws_cognito as cognito,
  aws_ec2 as ec2,
  aws_elasticache as elasticache,
  aws_kms as kms,
  aws_s3 as s3,
  aws_sns as sns,
  aws_ssm as ssm,
  RemovalPolicy,
  Stack,
  type StackProps,
} from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import type { Construct } from 'constructs';

/** PlatformStack のプロパティ。 */
export interface PlatformStackProps extends StackProps {
  /** 環境名（dev / prd）。removalPolicy を切り替える。 */
  envName: string;
}

export class PlatformStack extends Stack {
  constructor(scope: Construct, id: string, props: PlatformStackProps) {
    super(scope, id, props);

    const { envName } = props;
    const isProd = envName === 'prd';
    const removalPolicy = isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;

    // --- KMS（SECURITY-01）---
    const key = new kms.Key(this, 'PlatformKey', {
      enableKeyRotation: true,
      removalPolicy,
      description: `yudane-platform-${envName} 共通暗号化キー`,
    });

    // --- VPC（2 AZ / 3 層、SECURITY-07、Q1=A）---
    const vpc = new ec2.Vpc(this, 'PlatformVpc', {
      maxAzs: 2,
      natGateways: isProd ? 2 : 1,
      subnetConfiguration: [
        { name: 'public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
        { name: 'isolated', subnetType: ec2.SubnetType.PRIVATE_ISOLATED, cidrMask: 24 },
      ],
    });
    // VPC Endpoint（Lambda の依存先）
    vpc.addGatewayEndpoint('DynamoDbEndpoint', {
      service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
    });
    vpc.addGatewayEndpoint('S3Endpoint', { service: ec2.GatewayVpcEndpointAwsService.S3 });
    vpc.addInterfaceEndpoint('SecretsEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
    });
    vpc.addInterfaceEndpoint('CloudWatchLogsEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
    });

    // Lambda 用 Security Group
    const lambdaSg = new ec2.SecurityGroup(this, 'LambdaSg', {
      vpc,
      description: 'YUDANE Lambda 共通 SG',
      allowAllOutbound: true,
    });

    // --- Cognito User Pool（基盤のみ、MFA フローは Unit-2）---
    const userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `yudane-auth-${envName}-userpool`,
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      mfa: cognito.Mfa.REQUIRED,
      mfaSecondFactor: { otp: true, sms: false },
      passwordPolicy: { minLength: 12, requireSymbols: true, requireDigits: true },
      removalPolicy,
    });
    const userPoolClient = userPool.addClient('AppClient', {
      authFlows: { userSrp: true },
    });

    // --- S3（Data Lake / Catalog、SECURITY-01/09）---
    const dataLake = new s3.Bucket(this, 'DataLakeBucket', {
      bucketName: `yudane-platform-${envName}-datalake-${this.account}`,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: key,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      removalPolicy,
      autoDeleteObjects: !isProd,
    });

    // --- ElastiCache Redis（Q7=A: platform 配置、Unit-4/5 共有）---
    const redisSubnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      description: 'YUDANE Redis subnet group',
      subnetIds: vpc.selectSubnets({ subnetType: ec2.SubnetType.PRIVATE_ISOLATED }).subnetIds,
    });
    const redisSg = new ec2.SecurityGroup(this, 'RedisSg', {
      vpc,
      description: 'YUDANE Redis SG',
      allowAllOutbound: false,
    });
    redisSg.addIngressRule(lambdaSg, ec2.Port.tcp(6379), 'Lambda から Redis への接続のみ許可');
    const redis = new elasticache.CfnReplicationGroup(this, 'Redis', {
      replicationGroupDescription: `yudane-platform-${envName}-redis`,
      cacheNodeType: 'cache.t4g.micro',
      engine: 'redis',
      numNodeGroups: 1,
      replicasPerNodeGroup: isProd ? 1 : 0,
      automaticFailoverEnabled: isProd,
      atRestEncryptionEnabled: true,
      transitEncryptionEnabled: true,
      cacheSubnetGroupName: redisSubnetGroup.ref,
      securityGroupIds: [redisSg.securityGroupId],
    });

    // --- 観測（SECURITY-14）---
    const alertsTopic = new sns.Topic(this, 'AlertsTopic', {
      topicName: `yudane-platform-${envName}-alerts`,
      masterKey: key,
    });

    // --- SSM 出力（他 Unit が参照、shared-infrastructure.md §1）---
    this.publishParam('vpc-id', vpc.vpcId, envName);
    this.publishParam(
      'private-subnet-ids',
      vpc.selectSubnets({ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }).subnetIds.join(','),
      envName,
    );
    this.publishParam('userpool-id', userPool.userPoolId, envName);
    this.publishParam('userpool-client-id', userPoolClient.userPoolClientId, envName);
    this.publishParam('redis-endpoint', redis.attrPrimaryEndPointAddress, envName);
    this.publishParam('kms-key-arn', key.keyArn, envName);
    this.publishParam('alerts-topic-arn', alertsTopic.topicArn, envName);
    this.publishParam('lambda-sg-id', lambdaSg.securityGroupId, envName);

    this.applyNagSuppressions();
  }

  /** SSM Parameter として共有値を公開する。 */
  private publishParam(key: string, value: string, envName: string): void {
    new ssm.StringParameter(this, `Param-${key}`, {
      parameterName: `/yudane/${envName}/platform/${key}`,
      stringValue: value,
    });
  }

  /** cdk-nag の正当な抑制（理由コメント必須、tech-cdk §2）。 */
  private applyNagSuppressions(): void {
    NagSuppressions.addStackSuppressions(this, [
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'CDK が VPC / Bucket の自動生成リソースに付与する AWS 管理ポリシー。MVP では許容し、決勝前にカスタムポリシー化を検討（NFR-SEC SECURITY-06）',
      },
      {
        id: 'AwsSolutions-COG2',
        reason: 'MFA は REQUIRED で設定済み。COG2（MFA 未設定）は誤検出',
      },
    ]);
  }
}
