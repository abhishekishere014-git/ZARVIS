import { PROTOCOL_VERSION } from "@jarvis/protocol";

export type GatewayHealthStatus = "healthy" | "degraded" | "unhealthy";

export interface ComponentHealthInfo {
  status: GatewayHealthStatus;
  message?: string;
  details?: Record<string, unknown>;
}

export interface GatewayHealthReport {
  status: GatewayHealthStatus;
  timestamp: string;
  uptimeSeconds: number;
  components: {
    gateway: ComponentHealthInfo;
    protocol: ComponentHealthInfo;
    pythonCore: ComponentHealthInfo;
  };
}

export class HealthMonitor {
  private startTime = Date.now();
  private isGatewayRunning = false;
  private isPythonCoreConnected = false;
  private activeClientsCount = 0;

  public setGatewayRunning(running: boolean): void {
    this.isGatewayRunning = running;
  }

  public setPythonCoreConnected(connected: boolean): void {
    this.isPythonCoreConnected = connected;
  }

  public setActiveClientsCount(count: number): void {
    this.activeClientsCount = count;
  }

  public getReport(): GatewayHealthReport {
    const gatewayHealth: ComponentHealthInfo = {
      status: this.isGatewayRunning ? "healthy" : "unhealthy",
      details: {
        activeClients: this.activeClientsCount,
      },
    };

    const protocolHealth: ComponentHealthInfo = {
      status: "healthy",
      details: {
        supportedVersion: PROTOCOL_VERSION,
      },
    };

    // Do not fake unavailable services as healthy: accurately report Python Core state
    const pythonCoreHealth: ComponentHealthInfo = {
      status: this.isPythonCoreConnected ? "healthy" : "degraded",
      message: this.isPythonCoreConnected
        ? "Connected to Python Core"
        : "Awaiting Python Core connection",
    };

    let overallStatus: GatewayHealthStatus = "healthy";
    if (!this.isGatewayRunning) {
      overallStatus = "unhealthy";
    } else if (!this.isPythonCoreConnected) {
      overallStatus = "degraded";
    }

    return {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      uptimeSeconds: Math.floor((Date.now() - this.startTime) / 1000),
      components: {
        gateway: gatewayHealth,
        protocol: protocolHealth,
        pythonCore: pythonCoreHealth,
      },
    };
  }
}
