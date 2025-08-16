# Railway Deployment Guide

## Quick Deployment to Railway

Railway is a modern platform that makes it easy to deploy your Nova Voice application. It's often simpler than AWS App Runner and provides excellent developer experience.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Railway CLI** (optional, for command-line deployment)
3. **Git repository** with your code

## Deployment Options

### Option 1: Railway Dashboard (Recommended)

1. **Connect Your Repository**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Choose "Deploy from GitHub repo"
   - Select your repository

2. **Configure Environment Variables**
   - Go to your project settings
   - Add the following environment variables:
   ```
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_REGION=us-east-1
   MODEL_ID=amazon.nova-sonic-v1:0
   PORT=8080
   ```

3. **Deploy**
   - Railway will automatically detect the Dockerfile
   - Click "Deploy" to start the build process
   - Wait for deployment to complete (2-5 minutes)

### Option 2: Railway CLI

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Deploy**
   ```bash
   ./railway-deploy.sh
   ```

### Option 3: Manual CLI Deployment

```bash
# Initialize Railway project
railway init

# Set environment variables
railway variables set AWS_ACCESS_KEY_ID=your_access_key_here
railway variables set AWS_SECRET_ACCESS_KEY=your_secret_key_here
railway variables set AWS_REGION=us-east-1
railway variables set MODEL_ID=amazon.nova-sonic-v1:0
railway variables set PORT=8080

# Deploy
railway up
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key | ✅ |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | ✅ |
| `AWS_REGION` | AWS region | ✅ |
| `MODEL_ID` | Bedrock model ID | ✅ |
| `PORT` | Application port | ✅ |

### Railway Configuration

The `railway.json` file configures:
- **Builder**: Uses Dockerfile for containerization
- **Health Check**: Monitors `/` endpoint
- **Restart Policy**: Automatically restarts on failure
- **Timeout**: 5 minutes for health checks

## Advantages of Railway

### ✅ **Pros:**
- **Simpler deployment** than AWS App Runner
- **Automatic HTTPS** and custom domains
- **Built-in monitoring** and logs
- **Easy environment variable management**
- **Git integration** with automatic deployments
- **Free tier** available
- **Global CDN** for fast access

### ⚠️ **Considerations:**
- **Cost**: Pay-per-use pricing (typically $5-20/month for small apps)
- **AWS Integration**: Still requires AWS credentials for Bedrock
- **Nova Sonic Access**: Same model access requirements as AWS

## Post-Deployment

### 1. **Access Your Application**
- Railway provides a unique URL (e.g., `https://nova-voice-production.up.railway.app`)
- You can add custom domains in the Railway dashboard

### 2. **Monitor Your Application**
- Check the "Deployments" tab for build status
- View logs in real-time
- Monitor resource usage

### 3. **Set Up Custom Domain (Optional)**
- Go to your project settings
- Add a custom domain
- Configure DNS records as instructed

## Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check build logs
   railway logs
   
   # Rebuild locally to test
   docker build -t nova-voice .
   ```

2. **Environment Variables**
   - Ensure all required variables are set
   - Check for typos in variable names
   - Verify AWS credentials are valid

3. **Port Issues**
   - Railway automatically sets `PORT` environment variable
   - Ensure your app listens on the correct port

4. **Nova Sonic Access**
   - Same issue as AWS App Runner
   - Contact AWS support for model access

### Useful Commands

```bash
# View logs
railway logs

# Check status
railway status

# Open in browser
railway open

# View variables
railway variables

# Redeploy
railway up
```

## Cost Optimization

### Railway Pricing
- **Free Tier**: $5 credit monthly
- **Pay-per-use**: Based on compute time and resources
- **Typical Cost**: $5-20/month for small applications

### Tips to Reduce Costs
1. **Use free tier** for development
2. **Monitor usage** in Railway dashboard
3. **Scale down** when not in use
4. **Use sleep mode** for development environments

## Security

### Best Practices
1. **Environment Variables**: Never commit secrets to Git
2. **AWS Credentials**: Use least-privilege IAM roles
3. **HTTPS**: Railway provides automatic SSL certificates
4. **Monitoring**: Set up alerts for unusual activity

### Railway Security Features
- **Automatic HTTPS** with Let's Encrypt
- **Environment variable encryption**
- **Git-based deployments** with audit trail
- **Built-in monitoring** and alerting

## Migration from AWS App Runner

If you're moving from AWS App Runner to Railway:

1. **Export environment variables** from AWS
2. **Update deployment scripts** to use Railway CLI
3. **Test thoroughly** before switching
4. **Update documentation** and team processes

## Support

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Community Discord**: [discord.gg/railway](https://discord.gg/railway)
- **GitHub Issues**: [github.com/railwayapp/cli](https://github.com/railwayapp/cli)

---

**Your Nova Voice application is now ready for Railway deployment!** 🚂✨
