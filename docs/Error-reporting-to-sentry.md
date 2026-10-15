---
id: Error-reporting-to-sentry
title: "Error reporting to sentry"
sidebar_label: "Error reporting to sentry"
---

# Overview

Since [probably 3.65](https://github.com/seaweedfs/seaweedfs/commit/953f5713490343f3cb4d36eb17bae9e8716068b4) release will be possible to send errors to sentry.

To enable reporting some environment variables must be set
* SENTRY_DSN (from project settings)
* SENTRY_ENVIRONMENT (production, prod, test or whatever is used in organization)
* SENTRY_RELEASE (weed@3.64)

No other settings involved at this moment.

SENTRY_DSN is the only required option and could be obtained from project settings.

SENTRY_ENVIRONMENT and SENTRY_RELEASE may be empty or not set at all.
Assign it to what match your organization's flow.