# Proposal: UI Enhancement & Manual Mode Fix

## Background
Template Filler Web UI 需要进一步优化用户体验。

## Problem
1. **界面布局** - 占位符配置区域布局不够美观
2. **手动模式重新生成** - 修改手动输入后点击重新生成不会更新结果

## Goals
1. 优化占位符配置的 UI 布局，提升视觉效果
2. 修复手动模式下重新生成按钮的行为

## Proposed Solution

### 1. UI 布局优化
- 占位符配置卡片采用更紧凑的布局
- 使用更清晰的视觉分隔
- 优化模式选择器和输入框的对齐

### 2. 手动模式重新生成修复
- 重新生成时读取当前输入框的最新值
- 更新 session 中的 manualValue
- 确保结果面板显示最新的手动输入内容

## Scope

### In Scope
- `styles.css` - 占位符配置布局样式优化
- `app.js` - 重新生成时同步 manualValue
- `server.py` - regenerate API 支持更新 manualValue

### Out of Scope
- 新功能添加
- 后端逻辑重构
