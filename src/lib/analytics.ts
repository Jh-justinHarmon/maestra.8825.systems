/**
 * Analytics Module
 * Tracks user interactions and events for telemetry.
 * Currently logs to console; later integrates with backend telemetry service.
 */

export interface AnalyticsEvent {
  event: string;
  timestamp: string;
  props?: Record<string, unknown>;
}

/**
 * Track an analytics event.
 * @param event Event name (e.g., 'message_sent', 'capture_created')
 * @param props Optional event properties
 */
export function trackEvent(event: string, props?: Record<string, unknown>): void {
  const analyticsEvent: AnalyticsEvent = {
    event,
    timestamp: new Date().toISOString(),
    props,
  };

  // Log to console for now (development)
  console.log('[Analytics]', analyticsEvent);

  // TODO: Send to telemetry backend
  // fetch('/api/telemetry/events', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(analyticsEvent),
  // }).catch(err => console.error('Telemetry error:', err));
}

/**
 * Track when a message is sent.
 */
export function trackMessageSent(modeId: string, hasContext: boolean): void {
  trackEvent('message_sent', { modeId, hasContext });
}

/**
 * Track when a capture is created.
 */
export function trackCaptureCreated(modeId: string, focusType?: string): void {
  trackEvent('capture_created', { modeId, focusType });
}

/**
 * Track when a mode is selected.
 */
export function trackModeSelected(modeId: string, confidence: number): void {
  trackEvent('mode_selected', { modeId, confidence });
}

/**
 * Track when a handoff capsule is copied.
 */
export function trackHandoffCopied(captureId: string): void {
  trackEvent('handoff_copied', { captureId });
}

/**
 * Track when a pin is shared.
 */
export function trackPinShared(captureId: string, method: string): void {
  trackEvent('pin_shared', { captureId, method });
}
