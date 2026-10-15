---
id: Filer-JWT-Use
title: "Filer JWT Use"
sidebar_label: "Filer JWT Use"
---

## Introduction

See [the security overview](https://github.com/seaweedfs/seaweedfs/wiki/Security-Overview#securing-filer-http-with-jwt) for a more complete description.

## How to get a valid JWT

The Filer won't generate JWTs, you will have to configure another service to create a JWT with the same signing key set in the `security.toml` file described on the Security Configuration wiki page. When generating the JWT, ensure that the timeout in seconds matches the timeout set in the `security.toml` file.

## How to send a JWT to the Filer

The Filer supports receiving a JWT in three different forms:

1. Through the `Authorization: Bearer &lt;token&gt;` header
2. Via the request's query parameters: http://localhost:8888/buckets/all?jwt=token
3. In an HTTP-only cookie named AT(Access Token)


