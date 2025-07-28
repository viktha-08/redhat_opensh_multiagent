import logging
import logging.config

# Load logging configuration from file
logging.config.fileConfig("resources/logging.conf")

# Disable logging of imported packages
logging.getLogger("ibm_watsonx_ai.client").disabled = True
logging.getLogger("ibm_watsonx_ai.wml_resource").disabled = True
logging.getLogger("faiss.loader").disabled = True
logging.getLogger("httpcore.*").disabled = True

# Create logger
logger = logging.getLogger("AppLogger")