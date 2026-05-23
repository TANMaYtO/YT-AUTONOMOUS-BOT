# Cronus Web Frontend

The official web frontend for the Cronus autonomous YouTube Shorts generation agent. Built with Next.js 14 App Router, Supabase, and Tailwind CSS. The interface strictly adheres to a hyper-brutalist design language.

## Architecture

* **Framework:** Next.js 14 (App Router)
* **Authentication & Database:** Supabase (SSR integrated)
* **Styling:** Tailwind CSS (Zero border-radius, high-contrast brutalist design)
* **Components:** Custom brutalist adaptations of shadcn/ui and Radix primitives

## Prerequisites

* Node.js 18.17+
* A Supabase project with Authentication and PostgreSQL enabled
* YouTube Data API credentials for OAuth

## Quick Start

1. Clone the repository and install dependencies:
```bash
npm install
```

2. Configure environment variables:
Copy the provided `.env.local.example` to `.env.local` and populate the required keys:
```bash
cp .env.local.example .env.local
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

* `src/app/` - Next.js App Router pages and API routes
* `src/components/` - Reusable UI components and layouts
* `src/lib/` - Shared utilities, types, and Supabase client configurations
* `supabase/migrations/` - Database schema definitions

## Database Setup

Apply the SQL migration file located in `supabase/migrations/001_initial_schema.sql` to your Supabase project to initialize the required tables and Row Level Security (RLS) policies.

## Features

* **Authentication Flow:** Protected routes via Supabase SSR middleware
* **Onboarding Sequence:** Multi-step wizard for configuring niches, topics, and characters
* **YouTube Integration:** OAuth 2.0 flow with AES-GCM token encryption
* **Dashboard:** Centralized control panel for monitoring queue status, history, and agent health
* **Settings:** Configuration management for YouTube connections, posting schedules, and Telegram notifications

## Current Status

**Phase 2: Authentication & Onboarding has been successfully completed.**
* **Supabase Integration:** Full end-to-end SSR authentication is live.
* **Database Guards:** Strict, edge-cached routing guarantees users cannot reach the dashboard without completing all 3 setup stages (Pricing, YouTube Auth, Engine Config).
* **Config Storage:** Niche, topic, character, and schedule selections are now securely persisted to the user's `user_configs` table in Supabase via backend API routes.
* **Pricing Integration:** Fully designed brutalist pricing tier component successfully integrated.

## License

Proprietary and Confidential.
