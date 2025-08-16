# Nova Voice - AWS App Runner Deployment

A real-time voice chat application using AWS Bedrock's Nova Sonic model, deployed on AWS App Runner.

## Features

- 🎤 Real-time voice conversation with AI
- 🌐 WebSocket-based communication
- 🎨 Modern, responsive web interface
- 🤖 AI receptionist persona ("Saad" at TechCorp Solutions)
- ☁️ Cloud-native deployment on AWS App Runner

## Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed
- AWS account with access to:
  - AWS App Runner
  - Amazon ECR
  - AWS Secrets Manager
  - Amazon Bedrock (Nova Sonic model)

## Quick Deployment

### Option 1: Automated Deployment Script

```bash
# Make the script executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

### Option 2: Manual Deployment

#### 1. Build and Push Docker Image

```bash
# Build the image
docker build -t nova-voice:latest .

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository (if it doesn't exist)
aws ecr create-repository --repository-name nova-voice --region us-east-1

# Tag and push
ECR_REPO_URI=$(aws ecr describe-repositories --repository-names nova-voice --region us-east-1 --query 'repositories[0].repositoryUri' --output text)
docker tag nova-voice:latest $ECR_REPO_URI:latest
docker push $ECR_REPO_URI:latest
```

#### 2. Set Up AWS Secrets Manager

```bash
# Create secrets for AWS credentials
aws secretsmanager create-secret \
    --name "/nova-voice/aws-access-key-id" \
    --description "AWS Access Key ID for Nova Voice" \
    --secret-string "your_access_key_here" \
    --region us-east-1

aws secretsmanager create-secret \
    --name "/nova-voice/aws-secret-access-key" \
    --description "AWS Secret Access Key for Nova Voice" \
    --secret-string "your_secret_key_here" \
    --region us-east-1
```

#### 3. Deploy to App Runner

Use the AWS Console or AWS CLI to create an App Runner service with the following configuration:

- **Source**: ECR image
- **Port**: 8080
- **Environment Variables**:
  - `AWS_REGION`: us-east-1
  - `MODEL_ID`: amazon.nova-sonic-v1:0
- **Secrets**:
  - `AWS_ACCESS_KEY_ID`: /nova-voice/aws-access-key-id
  - `AWS_SECRET_ACCESS_KEY`: /nova-voice/aws-secret-access-key

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Application port | 8080 |
| `AWS_REGION` | AWS region | us-east-1 |
| `MODEL_ID` | Bedrock model ID | amazon.nova-sonic-v1:0 |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |

### AWS Permissions Required

The AWS credentials need the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-sonic-v1:0"
        }
    ]
}
```

## Local Development

### Prerequisites

- Python 3.11+
- Virtual environment

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.server.txt

# Set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Run the application
python server.py
```

### Access

- **Local**: http://localhost:8080
- **App Runner**: https://[service-id].us-east-1.awsapprunner.com

## Troubleshooting

### Common Issues

1. **Nova Sonic Model Access**
   - Ensure your AWS account has access to the Nova Sonic model
   - Contact AWS support if you need access to premium models

2. **WebSocket Connection Issues**
   - Check that the port 8080 is accessible
   - Verify CORS settings if accessing from different domains

3. **AWS Credentials**
   - Ensure credentials have proper Bedrock permissions
   - Check that secrets are properly configured in App Runner

### Logs

Check App Runner logs in the AWS Console for detailed error information.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   AWS App       │    │   AWS Bedrock   │
│                 │◄──►│   Runner        │◄──►│   Nova Sonic    │
│   WebSocket     │    │   (FastAPI)     │    │   Model         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Security Notes

- AWS credentials are stored in AWS Secrets Manager
- The application runs in a containerized environment
- WebSocket connections are secured via HTTPS in production
- No sensitive data is logged or stored

## License

This project is for demonstration purposes. Please ensure compliance with AWS terms of service and Bedrock model usage policies.
