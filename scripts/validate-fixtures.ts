/**
 * Fixture Validation Script
 * Validates all JSON fixtures in fixtures/v1/ against schema requirements.
 * 
 * Run: npm run validate:fixtures
 */

import * as fs from 'fs';
import * as path from 'path';

const SCHEMA_VERSION = '1';
const FIXTURES_DIR = path.join(process.cwd(), 'fixtures', 'v1');

interface ValidationResult {
  file: string;
  valid: boolean;
  errors: string[];
}

function isValidISOTimestamp(value: unknown): boolean {
  if (typeof value !== 'string') return false;
  const date = new Date(value);
  return !isNaN(date.getTime()) && value.includes('T');
}

function validateSchemaVersion(data: Record<string, unknown>, errors: string[]): void {
  if (!('schema_version' in data)) {
    errors.push('Missing required field: schema_version');
  } else if (data.schema_version !== SCHEMA_VERSION) {
    errors.push(`Invalid schema_version: expected "${SCHEMA_VERSION}", got "${data.schema_version}"`);
  }
}

function validateTimestamps(data: Record<string, unknown>, errors: string[], prefix = ''): void {
  for (const [key, value] of Object.entries(data)) {
    const fieldPath = prefix ? `${prefix}.${key}` : key;
    
    if (key === 'timestamp' || key.endsWith('_at')) {
      if (value !== null && !isValidISOTimestamp(value)) {
        errors.push(`Invalid ISO timestamp at ${fieldPath}: ${JSON.stringify(value)}`);
      }
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      validateTimestamps(value as Record<string, unknown>, errors, fieldPath);
    }
  }
}

function validateMessageFixture(data: Record<string, unknown>, errors: string[]): void {
  // User message format
  if ('role' in data && data.role === 'user') {
    if (!('id' in data)) errors.push('User message missing: id');
    if (!('content' in data)) errors.push('User message missing: content');
    if (!('timestamp' in data)) errors.push('User message missing: timestamp');
  }
  
  // Assistant response format (wrapped in Response)
  if ('message' in data && typeof data.message === 'object') {
    const msg = data.message as Record<string, unknown>;
    if (!('id' in msg)) errors.push('Response message missing: id');
    if (!('role' in msg)) errors.push('Response message missing: role');
    if (!('content' in msg)) errors.push('Response message missing: content');
    if (!('timestamp' in msg)) errors.push('Response message missing: timestamp');
  }
}

function validateCaptureFixture(data: Record<string, unknown>, errors: string[]): void {
  if (!('id' in data)) errors.push('Capture missing: id');
  if (!('title' in data)) errors.push('Capture missing: title');
  if (!('summary' in data)) errors.push('Capture missing: summary');
  if (!('timestamp' in data)) errors.push('Capture missing: timestamp');
}

function validateContextFixture(data: Record<string, unknown>, errors: string[]): void {
  if (!('relevantDocs' in data)) errors.push('Context missing: relevantDocs');
  if (!('suggestions' in data)) errors.push('Context missing: suggestions');
  if ('relevantDocs' in data && !Array.isArray(data.relevantDocs)) {
    errors.push('Context relevantDocs must be an array');
  }
  if ('suggestions' in data && !Array.isArray(data.suggestions)) {
    errors.push('Context suggestions must be an array');
  }
}

function validateFixture(filePath: string): ValidationResult {
  const relativePath = path.relative(FIXTURES_DIR, filePath);
  const errors: string[] = [];
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(content) as Record<string, unknown>;
    
    // All fixtures must have schema_version
    validateSchemaVersion(data, errors);
    
    // Validate timestamps are ISO format
    validateTimestamps(data, errors);
    
    // Type-specific validation based on directory
    if (filePath.includes('/messages/')) {
      validateMessageFixture(data, errors);
    } else if (filePath.includes('/capture/')) {
      validateCaptureFixture(data, errors);
    } else if (filePath.includes('/context/')) {
      validateContextFixture(data, errors);
    }
    
  } catch (err) {
    if (err instanceof SyntaxError) {
      errors.push(`Invalid JSON: ${err.message}`);
    } else {
      errors.push(`Failed to read file: ${(err as Error).message}`);
    }
  }
  
  return {
    file: relativePath,
    valid: errors.length === 0,
    errors,
  };
}

function findJsonFiles(dir: string): string[] {
  const files: string[] = [];
  
  if (!fs.existsSync(dir)) {
    return files;
  }
  
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...findJsonFiles(fullPath));
    } else if (entry.name.endsWith('.json')) {
      files.push(fullPath);
    }
  }
  
  return files;
}

function main(): void {
  console.log('🔍 Validating fixtures...\n');
  
  const jsonFiles = findJsonFiles(FIXTURES_DIR);
  
  if (jsonFiles.length === 0) {
    console.log('⚠️  No fixture files found in', FIXTURES_DIR);
    process.exit(1);
  }
  
  const results = jsonFiles.map(validateFixture);
  const passed = results.filter(r => r.valid);
  const failed = results.filter(r => !r.valid);
  
  // Print results
  for (const result of results) {
    if (result.valid) {
      console.log(`✅ ${result.file}`);
    } else {
      console.log(`❌ ${result.file}`);
      for (const error of result.errors) {
        console.log(`   └─ ${error}`);
      }
    }
  }
  
  // Summary
  console.log('\n' + '─'.repeat(50));
  console.log(`📊 Results: ${passed.length}/${results.length} fixtures valid`);
  
  if (failed.length > 0) {
    console.log(`\n❌ ${failed.length} fixture(s) failed validation`);
    process.exit(1);
  } else {
    console.log('\n✅ All fixtures valid!');
    process.exit(0);
  }
}

main();
