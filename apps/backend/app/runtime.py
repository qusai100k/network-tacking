from app.core.database import SessionLocal
from app.services.ai_analysis_service import AIAnalysisService
from app.services.ai_chat_service import AIChatService
from app.services.connection_analyzer_service import ConnectionAnalyzerService
from app.services.device_discovery_service import DeviceDiscoveryService
from app.services.geoip_service import GeoIPService
from app.services.host_network_service import HostNetworkService
from app.services.monitor_service import MonitorRuntime
from app.services.predictive_analytics_service import PredictiveAnalyticsService
from app.services.process_monitor_service import ProcessMonitorService
from app.services.vendor_lookup_service import VendorLookupService

host_network_service = HostNetworkService()
vendor_lookup_service = VendorLookupService()
geoip_service = GeoIPService()
predictive_analytics_service = PredictiveAnalyticsService()
device_discovery_service = DeviceDiscoveryService(host_network_service, vendor_lookup_service)
process_monitor_service = ProcessMonitorService(geoip_service, host_network_service)
connection_analyzer_service = ConnectionAnalyzerService(geoip_service)
ai_analysis_service = AIAnalysisService(predictive_analytics_service)
ai_chat_service = AIChatService()
monitor_runtime = MonitorRuntime(SessionLocal)