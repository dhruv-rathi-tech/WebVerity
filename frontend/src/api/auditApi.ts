import { AuditReport, AuditRequestOptions } from '../types/audit';
import { DEMO_AUDIT_ECOMMERCE, DEMO_AUDIT_HEALTHY } from '../mock/demoData';

const API_BASE = '/api';

export class AuditApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'AuditApiError';
  }
}

export const auditApi = {
  async checkHealth(): Promise<{ status: string; version: string }> {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error('Health check failed');
      return await res.json();
    } catch (err: any) {
      throw new AuditApiError(err.message || 'Cannot reach API backend');
    }
  },

  async runAudit(options: AuditRequestOptions): Promise<AuditReport> {
    const res = await fetch(`${API_BASE}/audit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(options),
    });

    if (!res.ok) {
      let errorMsg = `Server returned status ${res.status}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorMsg = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // use default error message
      }
      throw new AuditApiError(errorMsg, res.status);
    }

    return await res.json();
  },

  async getAuditById(auditId: string): Promise<AuditReport> {
    const res = await fetch(`${API_BASE}/audit/${auditId}`);
    if (!res.ok) {
      throw new AuditApiError(`Failed to retrieve audit ${auditId}`, res.status);
    }
    return await res.json();
  },

  async getAuditMarkdown(auditId: string): Promise<string> {
    const res = await fetch(`${API_BASE}/audit/${auditId}/report`);
    if (!res.ok) {
      throw new AuditApiError(`Failed to fetch report markdown`, res.status);
    }
    return await res.text();
  },

  getDemoReport(type: 'ecommerce' | 'healthy' = 'ecommerce'): AuditReport {
    if (type === 'healthy') return DEMO_AUDIT_HEALTHY;
    return DEMO_AUDIT_ECOMMERCE;
  }
};
