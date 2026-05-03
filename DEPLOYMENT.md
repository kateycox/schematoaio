# IBM Cloud Code Engine Deployment Guide

## Prerequisites
- IBM Cloud CLI installed ✓
- IBM Cloud account ✓
- Docker files created ✓

## Step-by-Step Deployment

### 1. Login to IBM Cloud
```bash
ibmcloud login
```
Follow the prompts to authenticate.

### 2. Install Code Engine Plugin (if not already installed)
```bash
ibmcloud plugin install code-engine
```

### 3. Create a Code Engine Project
```bash
ibmcloud ce project create --name schematoaio-project
```

### 4. Target the Project
```bash
ibmcloud ce project select --name schematoaio-project
```

### 5. Deploy the Application
From the `schematoaio` directory, run:
```bash
ibmcloud ce application create \
  --name schematoaio \
  --build-source . \
  --port 8080 \
  --min-scale 0 \
  --max-scale 1 \
  --cpu 0.25 \
  --memory 0.5G
```

### 6. Set Environment Variables
After deployment, add your environment variables:
```bash
# Read your .env file and set each variable
ibmcloud ce application update --name schematoaio \
  --env GEMINI_API_KEY=your_key_here \
  --env OPENAI_API_KEY=your_key_here
```

Or create a secret and reference it:
```bash
# Create secret from .env file
ibmcloud ce secret create --name app-secrets --from-env-file .env

# Update app to use secret
ibmcloud ce application update --name schematoaio --env-from-secret app-secrets
```

### 7. Get Your Application URL
```bash
ibmcloud ce application get --name schematoaio
```

Look for the URL in the output - it will look like:
`https://schematoaio.xyz123.us-south.codeengine.appdomain.cloud`

## Quick Commands

### View application status:
```bash
ibmcloud ce application get --name schematoaio
```

### View logs:
```bash
ibmcloud ce application logs --name schematoaio
```

### Update application (after code changes):
```bash
ibmcloud ce application update --name schematoaio --build-source .
```

### Delete application:
```bash
ibmcloud ce application delete --name schematoaio
```

## Troubleshooting

If deployment fails:
1. Check logs: `ibmcloud ce application logs --name schematoaio`
2. Verify environment variables are set
3. Ensure port 8080 is configured in Dockerfile
4. Check that all dependencies are in requirements.txt

## Cost
- Free tier: 100,000 vCPU-seconds/month
- With `--min-scale 0`, app scales to zero when not in use (saves resources)
- Typical usage should stay within free tier

## Share with Your Partner
Once deployed, simply share the application URL with your partner. She can access it directly in her browser - no setup required!