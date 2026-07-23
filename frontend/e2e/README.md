# E2E Tests with Playwright

This directory contains end-to-end tests for the FlatBOMGenerator plugin using Playwright.

## Setup

### Install Playwright

```bash
cd frontend
npm install
npx playwright install
```

### Install Browsers

```bash
npx playwright install --with-deps
```

## Running Tests

### Run all tests

```bash
npm run test:e2e
```

### Run tests with UI

```bash
npm run test:e2e:ui
```

### Debug tests

```bash
npm run test:e2e:debug
```

## Prerequisites

- InvenTree dev server must be running on http://localhost:8001
- Admin user must exist with credentials `admin/admin`
- Plugin must be installed and enabled in InvenTree

## Test Structure

- `example.spec.ts` - Basic example tests demonstrating Playwright setup
- Add more test files for specific plugin functionality

## Writing Tests

See [Playwright documentation](https://playwright.dev/docs/intro) for guidance on writing tests.

Key points:
- Use `data-testid` attributes for reliable element selection
- Test actual user workflows, not implementation details
- Keep tests independent and focused
- Use page objects for complex interactions
