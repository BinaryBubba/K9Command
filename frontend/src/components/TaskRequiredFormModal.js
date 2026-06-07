import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';

const TaskRequiredFormModal = ({ isOpen, onClose, task, onSuccess }) => {
  const [template, setTemplate] = useState(null);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !task?.form_template_id) return;

    const load = async () => {
      try {
        const res = await api.get(`/forms/templates/${task.form_template_id}`);
        setTemplate(res.data);
        setValues({});
      } catch (e) {
        console.error(e);
        toast.error("Failed to load form");
      }
    };

    load();
  }, [isOpen, task]);

  if (!isOpen || !task) return null;

  const handleChange = (key, value) => {
    setValues(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await api.post('/forms/submissions', {
        template_id: task.form_template_id,
        related_type: 'task',
        related_id: task.id,
        values,
        status: 'submitted',
      });

      await api.patch(`/tasks/${task.id}/complete`);

      toast.success("Task completed");
      onSuccess?.();
      onClose?.();
    } catch (err) {
      console.error(err);
      toast.error("Submit failed");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-xl w-full max-w-md">
        <h2 className="text-lg font-semibold mb-4">
          {template?.name || "Loading..."}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          {template?.fields?.map(field => {
            const key = field.key;
            const type = field.type;
            const value = values[key] || "";

            if (type === "select") {
              return (
                <select
                  key={key}
                  value={value}
                  onChange={e => handleChange(key, e.target.value)}
                  className="w-full border p-2 rounded"
                >
                  <option value="">Select...</option>
                  {field.options?.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              );
            }

            if (type === "boolean") {
              return (
                <label key={key} className="flex gap-2">
                  <input
                    type="checkbox"
                    checked={values[key] || false}
                    onChange={e => handleChange(key, e.target.checked)}
                  />
                  {field.label}
                </label>
              );
            }

            return (
              <input
                key={key}
                type={type === "number" ? "number" : "text"}
                placeholder={field.label}
                value={value}
                onChange={e =>
                  handleChange(
                    key,
                    type === "number" ? Number(e.target.value) : e.target.value
                  )
                }
                className="w-full border p-2 rounded"
              />
            );
          })}

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="border px-3 py-1 rounded">
              Cancel
            </button>
            <button type="submit" className="bg-blue-600 text-white px-3 py-1 rounded">
              Submit
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TaskRequiredFormModal;
