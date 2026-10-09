'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

const API =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Result = {
  workflow_id?: string;
  response?: string;
  risk_classification?: {
    risk_band?: string;
    probability_high_risk?: number;
    confidence?: number;
    reasons?: string[];
    recommended_action?: string;
  };
  validation?: {
    decision?: string;
    checks?: string[];
    issues?: string[];
  };
  sources?: Array<{
    document_id: string;
    title: string;
    section: string;
    text: string;
  }>;
  tool_results?: Array<{
    tool: string;
    status: string;
    promotion_id?: string;
  }>;
};

export default function Home() {
  const [q, setQ] = useState(
    'Classify promotion P-1003 for merchant approval'
  );
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [approvalDecision, setApprovalDecision] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setResult(null);
    setApprovalDecision(null);
    setApprovalError(null);

    try {
      const r = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'demo-ui',
          user_id: 'merchant-001',
          query: q,
        }),
      });

      const data = await r.json();

      if (!r.ok) {
        throw new Error(data.detail || 'Classification failed');
      }

      setResult(data);
    } catch (error) {
      setApprovalError(
        error instanceof Error ? error.message : 'Classification failed'
      );
    } finally {
      setLoading(false);
    }
  }

  async function approve(decision: 'APPROVE' | 'REJECT' | 'MODIFY') {
    if (!result?.workflow_id) return;

    setApprovalLoading(true);
    setApprovalError(null);

    try {
      const r = await fetch(
        `${API}/api/approval/${result.workflow_id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            decision,
            approver_id: 'merchant-001',
            comment:
              decision === 'APPROVE'
                ? 'Approved by merchant'
                : decision === 'REJECT'
                  ? 'Rejected by merchant'
                  : 'Modification requested by merchant',
          }),
        }
      );

      const data = await r.json();

      if (!r.ok) {
        throw new Error(data.detail || 'Approval request failed');
      }

      setApprovalDecision(decision);
      setResult((previous) =>
        previous
          ? {
              ...previous,
              response: data.response || previous.response,
            }
          : previous
      );
    } catch (error) {
      setApprovalError(
        error instanceof Error
          ? error.message
          : 'Approval request failed'
      );
    } finally {
      setApprovalLoading(false);
    }
  }

  const risk = result?.risk_classification?.risk_band;
  const needsHumanApproval =
    result?.validation?.decision === 'HUMAN_REVIEW' &&
    !approvalDecision;

  const stages = [
    'Triage',
    'Promotion Data',
    'Policy RAG',
    'Investigation',
    'Risk Classification',
    'Validation',
    'Human Approval',
    'Response',
  ];

  return (
    <main>
      <header>
        <div>
          <span className="eyebrow">AGENTIC RETAIL AI</span>
          <h1>Promotion Risk Studio</h1>
          <p>
            Classify planned promotions before merchant approval using
            multi-agent reasoning, policy RAG and human review.
          </p>
        </div>

        <span className="pill">LangGraph · RAG · HITL</span>
      </header>

      <section className="grid">
        <div className="card chat">
          <h2>Promotion request</h2>

          <textarea
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />

          <button onClick={run} disabled={loading}>
            {loading ? 'Running agents…' : 'Run classification'}
          </button>

          {result && (
            <>
              <div className={`risk ${risk?.toLowerCase()}`}>
                {risk || 'NEEDS INPUT'}
              </div>

              <div className="response">
                <ReactMarkdown>
                  {result.response || ''}
                </ReactMarkdown>
              </div>

              {needsHumanApproval && (
                <div className="approval-panel">
                  <h2>Human Approval Required</h2>

                  <div className="approval-summary">
                    <div>
                      <span>Promotion</span>
                      <strong>
                        {result.tool_results?.find(
                          (x) => x.tool === 'get_promotion'
                        )?.promotion_id || 'P-1003'}
                      </strong>
                    </div>

                    <div>
                      <span>Risk</span>
                      <strong>{risk || 'HIGH'}</strong>
                    </div>

                    <div>
                      <span>Probability</span>
                      <strong>
                        {Math.round(
                          (result.risk_classification
                            ?.probability_high_risk || 0) * 100
                        )}
                        %
                      </strong>
                    </div>

                    <div>
                      <span>Confidence</span>
                      <strong>
                        {Math.round(
                          (result.risk_classification?.confidence || 0) * 100
                        )}
                        %
                      </strong>
                    </div>
                  </div>

                  <p>
                    This promotion requires merchant review before
                    approval.
                  </p>

                  <div className="approval-actions">
                    <button
                      onClick={() => approve('APPROVE')}
                      disabled={approvalLoading}
                    >
                      Approve
                    </button>

                    <button
                      onClick={() => approve('REJECT')}
                      disabled={approvalLoading}
                    >
                      Reject
                    </button>

                    <button
                      onClick={() => approve('MODIFY')}
                      disabled={approvalLoading}
                    >
                      Modify
                    </button>
                  </div>
                </div>
              )}

              {approvalDecision && (
                <div className="approval-success">
                  <strong>
                    Merchant decision: {approvalDecision}
                  </strong>
                  <p>
                    The human approval step has been completed and
                    recorded.
                  </p>
                </div>
              )}

              {approvalError && (
                <div className="approval-error">
                  {approvalError}
                </div>
              )}
            </>
          )}
        </div>

        <div className="card">
          <h2>Workflow</h2>

          {stages.map((stage, i) => {
            let status = 'pending';

            if (!result) {
              status = 'pending';
            } else if (stage === 'Human Approval') {
              status = needsHumanApproval
                ? 'waiting'
                : 'complete';
            } else {
              status = 'complete';
            }

            return (
              <div className="stage" key={stage}>
                <span>{String(i + 1).padStart(2, '0')}</span>
                {stage}
                <b>
                  {status === 'complete'
                    ? '✓'
                    : status === 'waiting'
                      ? '⏳'
                      : '•'}
                </b>
              </div>
            );
          })}
        </div>

        <div className="card sources">
          <h2>Policy sources</h2>

          {(result?.sources || []).map((s) => (
            <div className="source" key={s.document_id}>
              <b>
                {s.document_id} · {s.title}
              </b>

              <small>{s.section}</small>

              <p>{s.text}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
