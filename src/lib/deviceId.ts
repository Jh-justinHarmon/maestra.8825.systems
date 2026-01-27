/**
 * Device ID Utility
 * Generates and persists a stable device identifier
 */

/**
 * Generate a stable device ID based on OS, username, and random salt
 * Format: hash(os + username + salt)
 */
async function generateDeviceId(): Promise<string> {
  // Get OS info
  const platform = navigator.platform || 'unknown';
  const userAgent = navigator.userAgent || 'unknown';
  
  // Generate random salt (only once per device)
  const salt = crypto.randomUUID();
  
  // Combine into a stable string
  const deviceString = `${platform}-${userAgent}-${salt}`;
  
  // Hash using SubtleCrypto
  const encoder = new TextEncoder();
  const data = encoder.encode(deviceString);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  
  // Convert to hex string
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  
  return `device_${hashHex.substring(0, 16)}`;
}

/**
 * Get or create device ID
 * Persists to localStorage
 */
export async function getOrCreateDeviceId(): Promise<string> {
  const STORAGE_KEY = 'maestra_device_id';
  
  // Check if device ID already exists
  const existingId = localStorage.getItem(STORAGE_KEY);
  if (existingId) {
    return existingId;
  }
  
  // Generate new device ID
  const deviceId = await generateDeviceId();
  
  // Persist to localStorage
  localStorage.setItem(STORAGE_KEY, deviceId);
  
  return deviceId;
}
