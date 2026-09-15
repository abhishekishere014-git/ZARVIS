export class MessageBuffer {
  private buffer = "";
  private readonly maxBytes: number;

  constructor(maxBytes: number = 10 * 1024 * 1024) {
    this.maxBytes = maxBytes;
  }

  public push(chunk: Buffer | string): string[] {
    const text = typeof chunk === "string" ? chunk : chunk.toString("utf-8");
    this.buffer += text;

    if (this.buffer.length > this.maxBytes) {
      this.buffer = "";
      throw new Error(`IPC incoming frame exceeded maximum limit of ${this.maxBytes} bytes`);
    }

    const messages: string[] = [];
    let newlineIndex: number;

    while ((newlineIndex = this.buffer.indexOf("\n")) !== -1) {
      const line = this.buffer.slice(0, newlineIndex).trim();
      this.buffer = this.buffer.slice(newlineIndex + 1);

      if (line.length > 0) {
        messages.push(line);
      }
    }

    return messages;
  }

  public clear(): void {
    this.buffer = "";
  }

  public static formatFrame(message: unknown): string {
    return JSON.stringify(message) + "\n";
  }
}
