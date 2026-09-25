---
name: no-comment
description: "No comments were writed while writing the code"
category: "development"
risk: "safe"
source: "custom"
tags:
  - planning
  - cleaning
  - filterization
tools:
  - antigravity
---

# 🚧 No Commenting Rule 

## Overview
This skill gives rule to the agentic AI that no comments were writed before/during/after the implementation on the code. For better and clean code although it is minus documentation.
So no more AI-ish comments for // or {/* */} or # or --

## When to Use
- Use when user wants to use this skill to the agents
- Don't use on existing comments that already there, do not remove it
- Just affecting the implementation, not general project

## How It Works

### 1. Pre-Implementation Phase
When the agent wants to implement/write the codes, the agent just remember that it don't wrote the comments


---

## Expected Input Format
```text
/no-comment [prompts]