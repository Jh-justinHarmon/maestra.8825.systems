# Maestra

An AI assistant interface with a "card" architecture built with React 18 + Vite.

## Overview

Maestra is a chat interface application featuring:
- **MaestraCard**: Main chat component with message list, auto-scroll, selection pills, and capture mode
- **HandoffCapsule**: Compact shareable output for conversation highlights
- **Pins Drawer**: Collapsible right drawer for saved snippets

## Tech Stack

- React 18 + TypeScript
- Vite for build/dev
- TailwindCSS for styling
- Lucide React for icons

## Project Structure

```
src/
├── adapters/          # API abstraction layer
│   ├── types.ts       # Adapter interface definitions
│   ├── mockAdapter.ts # Mock responses for testing
│   ├── webAdapter.ts  # Placeholder for real API
│   └── index.ts
├── components/        # React components
│   ├── MaestraCard.tsx
│   ├── HandoffCapsule.tsx
│   ├── PinsDrawer.tsx
│   ├── Header.tsx
│   └── index.ts
├── App.tsx           # Main application
├── main.tsx          # Entry point
└── index.css         # Global styles
```

## Running Locally

```bash
npm install
npm run dev
```

The app runs on port 5000.

## Design

- Dark theme (zinc-900 background, zinc-800 cards)
- Accent color: blue-500
- Clean, minimal, professional

## Recent Changes

- 2024-12-30: Initial project setup with MaestraCard, HandoffCapsule, and adapter pattern
