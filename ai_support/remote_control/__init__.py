"""Remote control server-side components.

This package provides a small job-queue API so client PCs (agents) can poll
for work and report results back. Designed for deployments where the server
cannot directly reach client PCs (NAT/firewall), so the client initiates.
"""
