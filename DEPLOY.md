# Vercel Deployment Guide

## 🚀 Quick Deploy

### Step 1: Install Vercel CLI
```bash
npm i -g vercel
```

### Step 2: Login to Vercel
```bash
vercel login
```

### Step 3: Deploy
```bash
# First deployment (preview)
vercel

# Production deployment
vercel --prod
```

## 📁 Required Files (All Present ✅)

- ✅ `api/index.py` - Main Flask application
- ✅ `requirements.txt` - Python dependencies
- ✅ `vercel.json` - Vercel configuration
- ✅ `runtime.txt` - Python version (3.12)
- ✅ `.gitignore` - Git ignore rules

## 🔧 Configuration

### vercel.json
- Routes configured for `/api/*` and `/*`
- Python build configured

### Database
- SQLite uses `/tmp/database.db` on Vercel (serverless file system)
- Database auto-creates on first request

## ⚠️ Important Notes

1. **SQLite on Serverless**: 
   - Database file is in `/tmp` directory
   - Data may not persist between cold starts
   - For production with persistent data, consider MongoDB/PostgreSQL

2. **First Request**: 
   - Database table auto-creates on first API call
   - Slight delay on first request (normal)

3. **Environment Variables**: 
   - No environment variables needed for basic setup
   - Optional: Set `DB_FILE` to customize database path

## ✅ Deployment Checklist

- [x] All unnecessary files deleted
- [x] SQLite configured for Vercel (`/tmp` directory)
- [x] vercel.json configured
- [x] requirements.txt updated (only Flask needed)
- [x] README.md created
- [x] .gitignore updated

## 🎉 Ready to Deploy!

Just run `vercel` and your API will be live! 🚀

