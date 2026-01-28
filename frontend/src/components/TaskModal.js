import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';

const TaskModal = ({ isOpen, onClose, task, onSuccess, isRecurring = false }) => {
  const [loading, setLoading] = useState(false);
  const [locations, setLocations] = useState([]);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    location_id: '',
    due_date: '',
    assigned_to: '',
    recurring: isRecurring,
    recurrence_pattern: 'daily',
  });

  useEffect(() => {
    if (isOpen) {
      fetchLocations();
      if (task) {
        setFormData({
          title: task.title || '',
          description: task.description || '',
          location_id: task.location_id || '',
          due_date: task.due_date?.split('T')[0] || '',
          assigned_to: task.assigned_to || '',
          recurring: false,
          recurrence_pattern: 'daily',
        });
      }
    }
  }, [isOpen, task]);

  const fetchLocations = async () => {
    try {
      const response = await api.get('/locations');
      setLocations(response.data);
      if (response.data.length > 0 && !task) {
        setFormData(prev => ({ ...prev, location_id: response.data[0].id }));
      }
    } catch (error) {
      toast.error('Failed to load locations');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null,
      };

      if (task) {
        await api.patch(`/tasks/${task.id}`, payload);
        toast.success('Task updated successfully');
      } else {
        if (formData.recurring) {
          // Create recurring tasks (e.g., for next 30 days)
          const days = formData.recurrence_pattern === 'daily' ? 30 : formData.recurrence_pattern === 'weekly' ? 12 : 6;
          const interval = formData.recurrence_pattern === 'daily' ? 1 : formData.recurrence_pattern === 'weekly' ? 7 : 14;
          
          for (let i = 0; i < days; i++) {
            const dueDate = new Date();
            dueDate.setDate(dueDate.getDate() + (i * interval));
            await api.post('/tasks', {
              ...payload,
              due_date: dueDate.toISOString(),
              title: `${payload.title} (${dueDate.toLocaleDateString()})`,
            });
          }
          toast.success(`Created ${days} recurring tasks`);
        } else {
          await api.post('/tasks', payload);
          toast.success('Task created successfully');
        }
      }
      onSuccess();
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save task');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{task ? 'Edit Task' : isRecurring ? 'Create Recurring Tasks' : 'Create Task'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>Title</Label>
            <Input
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="Task title"
              required
              className="mt-1"
            />
          </div>

          <div>
            <Label>Description</Label>
            <Textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Task description"
              className="mt-1"
              rows={3}
            />
          </div>

          <div>
            <Label>Location</Label>
            <select
              value={formData.location_id}
              onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
              className="w-full p-2 border rounded-xl mt-1"
              required
            >
              <option value="">Select location</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>{loc.name}</option>
              ))}
            </select>
          </div>

          {!task && (
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.recurring}
                  onChange={(e) => setFormData({ ...formData, recurring: e.target.checked })}
                />
                <span>Recurring Task</span>
              </label>
            </div>
          )}

          {formData.recurring && (
            <div>
              <Label>Recurrence Pattern</Label>
              <select
                value={formData.recurrence_pattern}
                onChange={(e) => setFormData({ ...formData, recurrence_pattern: e.target.value })}
                className="w-full p-2 border rounded-xl mt-1"
              >
                <option value="daily">Daily (30 days)</option>
                <option value="weekly">Weekly (12 weeks)</option>
                <option value="biweekly">Bi-weekly (6 months)</option>
              </select>
            </div>
          )}

          {!formData.recurring && (
            <div>
              <Label>Due Date</Label>
              <Input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                className="mt-1"
              />
            </div>
          )}

          <div className="flex gap-3 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : task ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default TaskModal;
