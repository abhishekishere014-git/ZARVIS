export type LogLevel = "debug" | "info" | "warn" | "error";

const LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

export interface StructuredLog {
  timestamp: string;
  level: LogLevel;
  component: string;
  message: string;
  requestId?: string;
  details?: unknown;
}

export class Logger {
  constructor(
    private readonly component: string,
    private readonly minLevel: LogLevel = "info"
  ) {}

  public debug(message: string, requestId?: string, details?: unknown): void {
    this.log("debug", message, requestId, details);
  }

  public info(message: string, requestId?: string, details?: unknown): void {
    this.log("info", message, requestId, details);
  }

  public warn(message: string, requestId?: string, details?: unknown): void {
    this.log("warn", message, requestId, details);
  }

  public error(message: string, requestId?: string, details?: unknown): void {
    this.log("error", message, requestId, details);
  }

  private log(level: LogLevel, message: string, requestId?: string, details?: unknown): void {
    if (LEVEL_PRIORITY[level] < LEVEL_PRIORITY[this.minLevel]) {
      return;
    }

    const entry: StructuredLog = {
      timestamp: new Date().toISOString(),
      level,
      component: this.component,
      message,
      ...(requestId ? { requestId } : {}),
      ...(details !== undefined ? { details } : {}),
    };

    const formatted = JSON.stringify(entry);
    if (level === "error") {
      console.error(formatted);
    } else {
      console.log(formatted);
    }
  }
}
