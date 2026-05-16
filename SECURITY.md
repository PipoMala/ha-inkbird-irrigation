# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please **do not** open a public issue. Instead:

1. Email the details to the maintainer
2. Include a description of the vulnerability
3. Provide steps to reproduce (if possible)
4. Allow time for a fix before public disclosure

## Security Considerations

### Credentials

- **Never** commit your Local Key or Device ID to public repositories
- The integration stores credentials locally in Home Assistant's encrypted config
- No credentials are sent to third parties

### Data Privacy

- This integration communicates **only** with your device on the local network
- No cloud services are used after initial setup
- No data leaves your network

### Local Key

- The Local Key is a device-specific secret from Tuya's platform
- If compromised, someone on your network could control your irrigation
- Change it by re-pairing the device if you suspect it's been exposed

## Supported Versions

| Version | Status |
|---------|--------|
| 0.1.x   | Current |

## Security Best Practices

1. **Set a static IP** for your IIC-600 to prevent IP conflicts
2. **Isolate IoT devices** on a separate VLAN if possible
3. **Keep HA updated** for security patches
4. **Don't share** your Local Key publicly

## Questions?

For security questions, please reach out privately rather than opening public issues.
