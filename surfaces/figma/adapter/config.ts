/**
 * Figma v2 Adapter Configuration
 */

import type { AdapterConfig } from './figmaV2Adapter';

export const FIGMA_ADAPTER_CONFIG: AdapterConfig = {
  endpoint: 'https://maestra.8825.systems/api/maestra/advisor/ask',
  timeout: 30000, // 30 seconds
  contract_version: '2.0.0'
};
