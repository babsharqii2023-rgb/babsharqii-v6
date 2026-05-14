'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface FormField {
  name: string;
  label: string;
  type: string;
}

interface FormStep {
  title: string;
  fields: FormField[];
}

interface FormWizardProps {
  steps: FormStep[];
  onSubmit: (data: Record<string, unknown>) => void;
}

const T = {
  card: '#0d0d1a',
  primary: '#0d7bb5',
  secondary: '#0a9b8a',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white90: 'rgba(255,255,255,0.9)',
  white08: 'rgba(255,255,255,0.08)',
  white15: 'rgba(255,255,255,0.15)',
};

export default function FormWizard({ steps, onSubmit }: FormWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;
  const progress = ((currentStep + 1) / steps.length) * 100;

  const handleChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleNext = () => {
    if (isLast) {
      onSubmit(formData);
    } else {
      setCurrentStep((s) => s + 1);
    }
  };

  const handlePrev = () => {
    setCurrentStep((s) => Math.max(0, s - 1));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        background: T.card,
        borderRadius: 12,
        border: `1px solid ${T.primary}22`,
        padding: 24,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Progress bar */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ color: T.text, fontSize: 13, fontWeight: 600 }}>
            Step {currentStep + 1} of {steps.length}
          </span>
          <span style={{ color: T.textDim, fontSize: 11, fontFamily: 'monospace' }}>
            {Math.round(progress)}%
          </span>
        </div>
        <div style={{
          width: '100%',
          height: 4,
          background: T.white08,
          borderRadius: 2,
          overflow: 'hidden',
        }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
            style={{
              height: '100%',
              background: `linear-gradient(90deg, ${T.primary}, ${T.secondary})`,
              borderRadius: 2,
              boxShadow: `0 0 8px ${T.primary}44`,
            }}
          />
        </div>
      </div>

      {/* Step dots */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, justifyContent: 'center' }}>
        {steps.map((_, i) => (
          <motion.div
            key={i}
            animate={{
              width: i === currentStep ? 24 : 8,
              background: i === currentStep ? T.primary : i < currentStep ? T.secondary : T.white15,
            }}
            transition={{ duration: 0.3 }}
            style={{
              height: 8,
              borderRadius: 4,
              cursor: 'pointer',
            }}
            onClick={() => i < currentStep && setCurrentStep(i)}
          />
        ))}
      </div>

      {/* Step title */}
      <h3 style={{ color: T.white90, fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
        {step.title}
      </h3>

      {/* Fields */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
          transition={{ duration: 0.25 }}
          style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
        >
          {step.fields.map((field) => (
            <div key={field.name} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ color: T.textDim, fontSize: 12, fontWeight: 500 }}>{field.label}</label>
              {field.type === 'textarea' ? (
                <textarea
                  value={(formData[field.name] as string) || ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: `1px solid ${T.white15}`,
                    borderRadius: 8,
                    padding: '8px 12px',
                    color: T.text,
                    fontSize: 13,
                    outline: 'none',
                    resize: 'vertical',
                    minHeight: 72,
                    fontFamily: 'inherit',
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = T.primary; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = T.white15; }}
                />
              ) : (
                <input
                  type={field.type}
                  value={(formData[field.name] as string) || ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: `1px solid ${T.white15}`,
                    borderRadius: 8,
                    padding: '8px 12px',
                    color: T.text,
                    fontSize: 13,
                    outline: 'none',
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = T.primary; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = T.white15; }}
                />
              )}
            </div>
          ))}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={handlePrev}
          disabled={currentStep === 0}
          style={{
            padding: '8px 20px',
            borderRadius: 8,
            background: T.white08,
            color: currentStep === 0 ? T.textDim : T.text,
            border: `1px solid ${T.white15}`,
            cursor: currentStep === 0 ? 'not-allowed' : 'pointer',
            fontSize: 13,
            fontWeight: 500,
            opacity: currentStep === 0 ? 0.5 : 1,
          }}
        >
          ← Previous
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={handleNext}
          style={{
            padding: '8px 24px',
            borderRadius: 8,
            background: isLast
              ? `linear-gradient(135deg, ${T.secondary}, ${T.primary})`
              : T.primary,
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
            fontSize: 13,
            fontWeight: 600,
            boxShadow: `0 0 12px ${T.primary}44`,
          }}
        >
          {isLast ? 'Submit ✓' : 'Next →'}
        </motion.button>
      </div>
    </motion.div>
  );
}
