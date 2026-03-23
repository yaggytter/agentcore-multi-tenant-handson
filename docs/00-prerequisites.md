# チャプター 00: 前提条件・環境構築

本チャプターでは、ハンズオンを進めるために必要な環境の準備を行います。

## 目次

- [必要な IAM 権限](#必要な-iam-権限)
- [必要なツール](#必要なツール)
- [Bedrock モデルアクセスの有効化](#bedrock-モデルアクセスの有効化)
- [リージョン設定](#リージョン設定)
- [Python パッケージのインストール](#python-パッケージのインストール)
- [AWS CLI の設定](#aws-cli-の設定)
- [CDK ブートストラップ](#cdk-ブートストラップ)
- [確認手順](#確認手順)

---

## 必要な IAM 権限

ハンズオンで使用する IAM ユーザーまたはロールに、以下の管理ポリシーをアタッチしてください。

### 必須ポリシー

| ポリシー名 | 用途 |
|-----------|------|
| `BedrockAgentCoreFullAccess` | AgentCore の全機能（Runtime、Gateway、Memory 等）へのアクセス |
| `AmazonBedrockFullAccess` | Bedrock Foundation Model の呼び出し |

### 追加で必要なポリシー

| ポリシー名 | 用途 |
|-----------|------|
| `AWSLambda_FullAccess` | Lambda 関数の作成・管理 |
| `AWSCloudFormationFullAccess` | CDK によるスタックデプロイ |
| `IAMFullAccess` | CDK が作成するロール・ポリシーの管理 |
| `AmazonS3FullAccess` | CDK アセットの格納 |

### IAM ポリシーのアタッチ方法

```bash
# 使用する IAM ユーザー名を設定
IAM_USER="your-iam-user"

# 必須ポリシーのアタッチ
aws iam attach-user-policy \
  --user-name ${IAM_USER} \
  --policy-arn arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess

aws iam attach-user-policy \
  --user-name ${IAM_USER} \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-user-policy \
  --user-name ${IAM_USER} \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

aws iam attach-user-policy \
  --user-name ${IAM_USER} \
  --policy-arn arn:aws:iam::aws:policy/AWSCloudFormationFullAccess
```

> **注意**: 本番環境では最小権限の原則に従い、必要最低限の権限のみを付与してください。本ハンズオンではフルアクセスポリシーを使用しますが、これは学習目的に限定してください。

---

## 必要なツール

以下のツールをインストールしてください。

### Python 3.10+

```bash
python --version
# Python 3.10.x 以上であること
```

インストールされていない場合:

```bash
# macOS (Homebrew)
brew install python@3.12

# Ubuntu/Debian
sudo apt update && sudo apt install python3.12 python3.12-venv
```

### Node.js 20+

CDK CLI の実行に必要です。

```bash
node --version
# v20.x.x 以上であること
```

インストールされていない場合:

```bash
# macOS (Homebrew)
brew install node@20

# nvm を使用する場合
nvm install 20
nvm use 20
```

### AWS CDK CLI

```bash
npm install -g aws-cdk
cdk --version
# 2.x.x 以上であること
```

### AWS CLI v2

```bash
aws --version
# aws-cli/2.x.x 以上であること
```

インストール手順は [AWS CLI の公式ドキュメント](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) を参照してください。

### Docker

AgentCore Runtime のローカルテストに使用します。

```bash
docker --version
# Docker version 24.x.x 以上であること
```

Docker Desktop が起動していることを確認してください。

```bash
docker info
# エラーが出ないことを確認
```

---

## Bedrock モデルアクセスの確認

本ハンズオンでは **Claude Sonnet 4.6** を使用します。

> **Note**: 2025年9月以降、Amazon Bedrock のモデルアクセス承認は不要になりました。すべてのサーバーレスモデルは自動的に有効化されています。ただし、**Anthropic モデルの初回利用時**には、利用目的フォーム（First Time Use）の提出が必要です。

### 初回利用時の手順（アカウントにつき1回のみ）

1. AWS マネジメントコンソールにログイン
2. リージョンを **us-east-1（バージニア北部）** に切り替え
3. **Amazon Bedrock** サービスに移動
4. 左メニューの **「モデルカタログ」** から Anthropic の Claude モデルを選択
5. 初回の場合、利用目的フォームが表示されるので必要事項を入力して送信
6. 送信後、**即座に**利用可能になります（承認待ちはありません）

> **注意**: このフォーム提出を行わないと、API 呼び出しが約15分後に `403` エラーになります。

### CLI で確認

```bash
# クロスリージョン推論プロファイルの確認
aws bedrock list-inference-profiles \
  --region us-east-1 \
  --query "inferenceProfileSummaries[?inferenceProfileId=='us.anthropic.claude-sonnet-4-6'].{ProfileId:inferenceProfileId,Status:status}" \
  --output table
```

ステータスが `ACTIVE` であれば利用可能です。

> **注意**: Claude Sonnet 4.6 はクロスリージョン推論プロファイル経由でのアクセスが必要です。モデルIDとして `us.anthropic.claude-sonnet-4-6` を使用してください。

---

## リージョン設定

本ハンズオンでは **us-east-1（バージニア北部）** リージョンを使用します。

AgentCore は現時点で利用可能なリージョンが限定されています。us-east-1 を使用することで、全ての機能が利用可能です。

```bash
export AWS_DEFAULT_REGION=us-east-1
export AWS_REGION=us-east-1
```

`.bashrc` または `.zshrc` に追加しておくことを推奨します。

---

## Python パッケージのインストール

### 仮想環境の作成

```bash
cd /path/to/agentcore-multi-tenant-handson
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 必要パッケージのインストール

```bash
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

各パッケージの役割:

| パッケージ | 役割 |
|-----------|------|
| `bedrock-agentcore` | AgentCore SDK。Runtime、Gateway、Memory 等の操作 |
| `strands-agents` | Strands Agents フレームワーク。エージェントの構築 |
| `bedrock-agentcore-starter-toolkit` | AgentCore CLI ツール (`agentcore` コマンド) |

### インストール確認

```bash
pip list | grep -E "bedrock-agentcore|strands-agents"
```

以下のパッケージが表示されれば成功です:

```
bedrock-agentcore          x.x.x
bedrock-agentcore-starter-toolkit  x.x.x
strands-agents             x.x.x
```

### AgentCore CLI の確認

```bash
agentcore --help
```

使用可能なコマンド一覧が表示されれば正常にインストールされています。

---

## AWS CLI の設定

### プロファイルの設定

```bash
aws configure
# AWS Access Key ID: <アクセスキーを入力>
# AWS Secret Access Key: <シークレットキーを入力>
# Default region name: us-east-1
# Default output format: json
```

### 接続確認

```bash
aws sts get-caller-identity
```

以下のような出力が得られれば設定完了です:

```json
{
    "UserId": "AIDAXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

### Bedrock 接続確認

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[0].modelId" \
  --output text
```

モデル ID が返されれば Bedrock へのアクセスが確認できます。

---

## CDK ブートストラップ

AWS CDK を初めて使用するアカウント・リージョンでは、ブートストラップが必要です。

```bash
# アカウント ID を取得
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# CDK ブートストラップ
cdk bootstrap aws://${ACCOUNT_ID}/us-east-1
```

成功すると以下のような出力が得られます:

```
 ⏳  Bootstrapping environment aws://123456789012/us-east-1...
 ✅  Environment aws://123456789012/us-east-1 bootstrapped.
```

---

## 確認手順

全ての前提条件が揃っているか確認します。以下のコマンドを順に実行してください。

```bash
echo "=== 環境確認 ==="

echo "1. Python バージョン"
python --version

echo "2. Node.js バージョン"
node --version

echo "3. AWS CDK バージョン"
cdk --version

echo "4. AWS CLI バージョン"
aws --version

echo "5. Docker バージョン"
docker --version

echo "6. AgentCore CLI"
agentcore --help | head -5

echo "7. AWS 認証"
aws sts get-caller-identity

echo "8. Bedrock アクセス"
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'claude')].modelId" \
  --output text

echo "=== 確認完了 ==="
```

### チェックリスト

- [ ] Python 3.10+ がインストールされている
- [ ] Node.js 20+ がインストールされている
- [ ] AWS CDK CLI がインストールされている
- [ ] AWS CLI v2 がインストールされている
- [ ] Docker がインストールされ、起動している
- [ ] `bedrock-agentcore`、`strands-agents`、`bedrock-agentcore-starter-toolkit` がインストールされている
- [ ] AWS CLI が正しく設定されている（`aws sts get-caller-identity` が成功する）
- [ ] Bedrock の Anthropic 初回利用フォーム（FTU）が提出済みである
- [ ] CDK ブートストラップが完了している
- [ ] リージョンが `us-east-1` に設定されている

全ての項目にチェックが入ったら、[チャプター 01: アーキテクチャ概要](01-architecture-overview.md) に進んでください。
