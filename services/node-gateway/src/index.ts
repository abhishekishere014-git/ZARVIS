import { loadConfig } from "./config.js";
import { NodeGateway } from "./gateway.js";
import { Logger } from "./logger.js";

async function main() {
  const config = loadConfig();
  const logger = new Logger("jarvis.gateway.main", config.logLevel);

  logger.info("Initializing JARVIS Node Gateway...");
  const gateway = new NodeGateway(config);

  const handleShutdown = async (signal: string) => {
    logger.info(`Received ${signal}, shutting down gateway gracefully...`);
    try {
      await gateway.stop();
      process.exit(0);
    } catch (err) {
      logger.error("Error during gateway shutdown", undefined, String(err));
      process.exit(1);
    }
  };

  process.on("SIGINT", () => handleShutdown("SIGINT"));
  process.on("SIGTERM", () => handleShutdown("SIGTERM"));

  try {
    await gateway.start();
  } catch (err) {
    logger.error("Failed to start gateway", undefined, String(err));
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Unhandled error in gateway process:", err);
  process.exit(1);
});
