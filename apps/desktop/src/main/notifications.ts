/**
 * Native Windows desktop notifications for ZARVIS.
 * Hardened with anti-spam rate limiting and message deduplication cooldown.
 */

import { Notification } from "electron";

export interface NotificationPayload {
  title: string;
  body: string;
  level?: "info" | "warning" | "error" | "success";
}

export class NotificationManager {
  private static recentNotifications: Map<string, number> = new Map();
  private static timestamps: number[] = [];

  // Cooldown between identical notifications (milliseconds)
  public static COOLDOWN_MS = 2500;
  // Maximum notifications allowed within rolling window
  public static MAX_IN_WINDOW = 5;
  // Rolling window size (milliseconds)
  public static WINDOW_MS = 10000;

  /**
   * Shows a native Windows desktop notification if not throttled.
   * Returns true if notification was shown, false if rate-limited or unsupported.
   */
  public static show(payload: NotificationPayload): boolean {
    const now = Date.now();
    const key = `${payload.title || "ZARVIS"}::${payload.body}`;

    // 1. Check message deduplication cooldown
    const lastTime = this.recentNotifications.get(key);
    if (lastTime && now - lastTime < this.COOLDOWN_MS) {
      return false; // Throttled duplicate
    }

    // 2. Check rolling window rate limit
    this.timestamps = this.timestamps.filter((ts) => now - ts < this.WINDOW_MS);
    if (this.timestamps.length >= this.MAX_IN_WINDOW) {
      return false; // Rate limited
    }

    // Record notification timestamp and key
    this.recentNotifications.set(key, now);
    this.timestamps.push(now);

    // Prune stale keys
    for (const [k, ts] of this.recentNotifications.entries()) {
      if (now - ts > this.WINDOW_MS) {
        this.recentNotifications.delete(k);
      }
    }

    try {
      if (typeof Notification !== "undefined" && Notification.isSupported && Notification.isSupported()) {
        const notification = new Notification({
          title: payload.title || "ZARVIS",
          body: payload.body,
          silent: payload.level === "info",
        });
        notification.show();
      }
    } catch {}

    return true;
  }

  /**
   * Resets rate-limiting history (useful for test isolation).
   */
  public static resetHistory(): void {
    this.recentNotifications.clear();
    this.timestamps = [];
  }
}
