# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in TeslaOnTarget, please:

1. **DO NOT** open a public issue
2. Email the details to: joshuafuller@gmail.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to expect:
- Acknowledgment within 48 hours
- Status update within 7 days
- Fix typically within 30 days (depending on severity)

## Security Considerations

### Current Limitations (v1.0)
- **Plaintext TCP Only**: TAK communication is unencrypted
- **Local Network Only**: Should not be exposed to internet
- **No TAK Authentication**: Relies on network security

### Best Practices
1. Run on same network as TAK server
2. Use firewall rules to restrict access
3. Keep Tesla credentials secure (never commit cache.json)
4. Use VPN for any remote access
5. Monitor logs for suspicious activity

### Planned Security Improvements (v2.0)
- SSL/TLS support for TAK connections
- Certificate-based authentication
- Encrypted credential storage

## Dependency Updates

This project uses Dependabot to automatically:
- Monitor for security vulnerabilities
- Update dependencies weekly
- Create pull requests for updates

Security updates are prioritized and merged quickly.