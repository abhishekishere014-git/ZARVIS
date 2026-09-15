/**
 * Native Windows desktop notifications for ZARVIS.
 */

import { Notification } from "electron";

export interface NotificationPayload {
  title: string;
  body: string;
  level?: "info" | "warning" | "error" | "success";
}

export class NotificationManager {
  public static show(payload: NotificationPayload): void {
    if (!Notification.isSupported()) return;

    const notification = new Notification({
      title: payload.title || "ZARVIS",
      body: payload.body,
      silent: payload.level === "info",
    });

    notification.show();
  }
}
