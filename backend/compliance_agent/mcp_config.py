"""Knowledge Catalogue (Dataplex) MCP Toolbox configuration for Compliance agent.

When Agent Gateway is enabled, this MCP server provides semantic table discovery
so the Compliance agent can discover regulatory data schemas without hardcoded SQL.

Usage:
    Requires MCP Toolbox for Dataplex. When available, connect via:
    toolbox serve --config=backend/compliance_agent/mcp_toolbox_config.yaml

Status: Configured but not active — requires MCP Toolbox installation and
        Knowledge Catalogue entries for the regulatory tables.
"""

PROJECT = "general-ak"
LOCATION = "us-central1"

# Knowledge Catalogue entry point for regulatory data
KNOWLEDGE_CATALOGUE_CONFIG = {
    "project": PROJECT,
    "location": LOCATION,
    "entry_group": "cymbal-wealth-regulatory",
    "description": "Cymbal Wealth regulatory reporting tables metadata",
    "tables": {
        "capital_adequacy": {
            "description": "Basel III capital adequacy data — CRAR, Tier 1/2 capital, RWA",
            "source": "aws-redshift-serverless/cymbalwealth",
            "tags": ["crar", "basel3", "capital", "rbi"],
        },
        "liquidity_ratios": {
            "description": "Liquidity coverage ratios — LCR, NSFR, HQLA",
            "source": "aws-redshift-serverless/cymbalwealth",
            "tags": ["lcr", "nsfr", "liquidity"],
        },
        "npa_summary": {
            "description": "Non-performing assets summary — Gross NPA, Net NPA, provision coverage",
            "source": "aws-redshift-serverless/cymbalwealth",
            "tags": ["npa", "asset-quality", "provisions"],
        },
    },
}


def get_mcp_toolbox_config() -> dict:
    """Returns MCP Toolbox configuration for Knowledge Catalogue integration.

    When MCP Toolbox is installed and Agent Gateway is enabled, this config
    allows the Compliance agent to discover regulatory table schemas semantically
    instead of relying on hardcoded SQL.
    """
    return {
        "toolbox": {
            "serverAddress": "0.0.0.0:5000",
        },
        "sources": {
            "knowledge-catalogue": {
                "kind": "dataplex",
                "project": PROJECT,
                "location": LOCATION,
            }
        },
        "tools": [
            {
                "name": "discover_regulatory_tables",
                "kind": "dataplex-search",
                "source": "knowledge-catalogue",
                "description": "Search Knowledge Catalogue for regulatory compliance data tables",
            }
        ],
    }
