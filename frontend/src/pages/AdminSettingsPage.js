import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  ArrowLeftIcon, SettingsIcon, DollarSignIcon, CalendarIcon, 
  SaveIcon, PlusIcon, TrashIcon, EditIcon
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminSettingsPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Settings
  const [settings, setSettings] = useState({});
  const [pricingRules, setPricingRules] = useState([]);
  const [serviceTypes, setServiceTypes] = useState([]);
  const [meetGreetSettings, setMeetGreetSettings] = useState({
    required_for_new_customers: true,
    duration_minutes: 30,
    price: 0,
    available_days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    available_times: ['10:00', '14:00', '16:00'],
  });
  
  // Modal
  const [pricingModalOpen, setPricingModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [ruleForm, setRuleForm] = useState({
    name: '',
    rule_type: 'weekend',
    modifier_type: 'percentage',
    modifier_value: 10,
    start_date: '',
    end_date: '',
    active: true,
  });

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchAllData();
  }, [user, navigate]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [settingsRes, rulesRes, typesRes] = await Promise.all([
        api.get('/admin/settings'),
        api.get('/admin/pricing-rules').catch(() => ({ data: [] })),
        api.get('/service-types').catch(() => ({ data: [] })),
      ]);
      
      setSettings(settingsRes.data || {});
      setPricingRules(rulesRes.data || []);
      setServiceTypes(typesRes.data || []);
      
      // Load meet & greet settings from system settings
      const mgSettings = settingsRes.data?.meet_greet_settings;
      if (mgSettings) {
        try {
          setMeetGreetSettings(JSON.parse(mgSettings.value));
        } catch (e) {}
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSetting = async (key, value) => {
    try {
      await api.patch(`/admin/settings/${key}?value=${encodeURIComponent(value)}`);
      toast.success('Setting saved');
      setSettings(prev => ({
        ...prev,
        [key]: { ...prev[key], value }
      }));
    } catch (error) {
      toast.error('Failed to save setting');
    }
  };

  const handleSaveMeetGreetSettings = async () => {
    setSaving(true);
    try {
      await api.patch(`/admin/settings/meet_greet_settings?value=${encodeURIComponent(JSON.stringify(meetGreetSettings))}`);
      toast.success('Meet & Greet settings saved');
    } catch (error) {
      toast.error('Failed to save Meet & Greet settings');
    } finally {
      setSaving(false);
    }
  };

  const handleCreatePricingRule = async () => {
    try {
      if (editingRule) {
        await api.patch(`/admin/pricing-rules/${editingRule.id}`, ruleForm);
        toast.success('Pricing rule updated');
      } else {
        await api.post('/admin/pricing-rules', ruleForm);
        toast.success('Pricing rule created');
      }
      setPricingModalOpen(false);
      setEditingRule(null);
      setRuleForm({
        name: '',
        rule_type: 'weekend',
        modifier_type: 'percentage',
        modifier_value: 10,
        start_date: '',
        end_date: '',
        active: true,
      });
      fetchAllData();
    } catch (error) {
      toast.error('Failed to save pricing rule');
    }
  };

  const handleDeletePricingRule = async (ruleId) => {
    if (!window.confirm('Are you sure you want to delete this pricing rule?')) return;
    try {
      await api.delete(`/admin/pricing-rules/${ruleId}`);
      toast.success('Pricing rule deleted');
      fetchAllData();
    } catch (error) {
      toast.error('Failed to delete pricing rule');
    }
  };

  const openEditRule = (rule) => {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name || '',
      rule_type: rule.rule_type || 'weekend',
      modifier_type: rule.modifier_type || 'percentage',
      modifier_value: rule.modifier_value || 10,
      start_date: rule.start_date || '',
      end_date: rule.end_date || '',
      active: rule.active !== false,
    });
    setPricingModalOpen(true);
  };

  const dayOptions = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F9F7F2]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button variant="ghost" onClick={() => navigate('/admin/dashboard')} className="flex items-center gap-2 mb-2">
            <ArrowLeftIcon size={18} /> Back to Dashboard
          </Button>
          <div className="flex items-center gap-3">
            <SettingsIcon className="text-primary" size={28} />
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">System Settings</h1>
              <p className="text-muted-foreground mt-1">Configure pricing, capacity, and business rules</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        <Tabs defaultValue="general">
          <TabsList className="mb-6">
            <TabsTrigger value="general">
              <SettingsIcon size={16} className="mr-2" /> General
            </TabsTrigger>
            <TabsTrigger value="pricing">
              <DollarSignIcon size={16} className="mr-2" /> Pricing
            </TabsTrigger>
            <TabsTrigger value="meet-greet">
              <CalendarIcon size={16} className="mr-2" /> Meet & Greet
            </TabsTrigger>
          </TabsList>

          {/* General Settings */}
          <TabsContent value="general">
            <div className="grid gap-6">
              {/* Capacity Settings */}
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardHeader>
                  <CardTitle>Capacity Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Room Capacity</Label>
                      <Input
                        type="number"
                        value={settings.rooms_capacity?.value || 7}
                        onChange={(e) => handleSaveSetting('rooms_capacity', e.target.value)}
                        className="mt-1"
                      />
                      <p className="text-xs text-muted-foreground mt-1">Max dogs per room</p>
                    </div>
                    <div>
                      <Label>Crate Capacity</Label>
                      <Input
                        type="number"
                        value={settings.crates_capacity?.value || 4}
                        onChange={(e) => handleSaveSetting('crates_capacity', e.target.value)}
                        className="mt-1"
                      />
                      <p className="text-xs text-muted-foreground mt-1">Max crates available</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Payment Settings */}
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardHeader>
                  <CardTitle>Payment Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Deposit Percentage</Label>
                      <Input
                        type="number"
                        value={settings.deposit_percentage?.value || 50}
                        onChange={(e) => handleSaveSetting('deposit_percentage', e.target.value)}
                        className="mt-1"
                      />
                      <p className="text-xs text-muted-foreground mt-1">Required deposit %</p>
                    </div>
                    <div>
                      <Label>Tax Rate (%)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={settings.tax_rate?.value || 0}
                        onChange={(e) => handleSaveSetting('tax_rate', e.target.value)}
                        className="mt-1"
                      />
                      <p className="text-xs text-muted-foreground mt-1">Applied to all bookings</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Booking Settings */}
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardHeader>
                  <CardTitle>Booking Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Require Approval for All Bookings</Label>
                      <p className="text-xs text-muted-foreground">All bookings require admin approval</p>
                    </div>
                    <Switch
                      checked={settings.booking_requires_approval?.value === 'true'}
                      onCheckedChange={(checked) => handleSaveSetting('booking_requires_approval', checked ? 'true' : 'false')}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Pricing Tab */}
          <TabsContent value="pricing">
            <div className="space-y-6">
              {/* Base Pricing */}
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Base Pricing</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>Room Rate (per dog/night)</Label>
                      <div className="flex items-center mt-1">
                        <span className="text-muted-foreground mr-2">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          value={settings.base_room_rate?.value || 45}
                          onChange={(e) => handleSaveSetting('base_room_rate', e.target.value)}
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Crate Rate (per dog/night)</Label>
                      <div className="flex items-center mt-1">
                        <span className="text-muted-foreground mr-2">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          value={settings.base_crate_rate?.value || 35}
                          onChange={(e) => handleSaveSetting('base_crate_rate', e.target.value)}
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Daycare Rate (per dog/day)</Label>
                      <div className="flex items-center mt-1">
                        <span className="text-muted-foreground mr-2">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          value={settings.base_daycare_rate?.value || 30}
                          onChange={(e) => handleSaveSetting('base_daycare_rate', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>Separate Playtime Add-on</Label>
                      <div className="flex items-center mt-1">
                        <span className="text-muted-foreground mr-2">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          value={settings.separate_playtime_rate?.value || 6}
                          onChange={(e) => handleSaveSetting('separate_playtime_rate', e.target.value)}
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Multi-Dog Discount (%)</Label>
                      <Input
                        type="number"
                        value={settings.multi_dog_discount?.value || 10}
                        onChange={(e) => handleSaveSetting('multi_dog_discount', e.target.value)}
                        className="mt-1"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Pricing Rules */}
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Pricing Rules</CardTitle>
                  <Button onClick={() => { setEditingRule(null); setPricingModalOpen(true); }}>
                    <PlusIcon size={16} className="mr-2" /> Add Rule
                  </Button>
                </CardHeader>
                <CardContent>
                  {pricingRules.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">No pricing rules configured</p>
                  ) : (
                    <div className="space-y-3">
                      {pricingRules.map(rule => (
                        <div key={rule.id} className="flex items-center justify-between p-4 bg-muted/20 rounded-lg">
                          <div>
                            <p className="font-medium">{rule.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {rule.rule_type} | {rule.modifier_type === 'percentage' ? `${rule.modifier_value}%` : `$${rule.modifier_value}`}
                              {rule.start_date && ` | ${rule.start_date} - ${rule.end_date}`}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            <Button variant="outline" size="sm" onClick={() => openEditRule(rule)}>
                              <EditIcon size={14} />
                            </Button>
                            <Button variant="destructive" size="sm" onClick={() => handleDeletePricingRule(rule.id)}>
                              <TrashIcon size={14} />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Meet & Greet Tab */}
          <TabsContent value="meet-greet">
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader>
                <CardTitle>Meet & Greet Requirements</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Require Meet & Greet for New Customers</Label>
                    <p className="text-xs text-muted-foreground">New customers must complete a meet & greet before booking stays</p>
                  </div>
                  <Switch
                    checked={meetGreetSettings.required_for_new_customers}
                    onCheckedChange={(checked) => setMeetGreetSettings({ ...meetGreetSettings, required_for_new_customers: checked })}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Duration (minutes)</Label>
                    <Input
                      type="number"
                      value={meetGreetSettings.duration_minutes}
                      onChange={(e) => setMeetGreetSettings({ ...meetGreetSettings, duration_minutes: parseInt(e.target.value) })}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>Price ($)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={meetGreetSettings.price}
                      onChange={(e) => setMeetGreetSettings({ ...meetGreetSettings, price: parseFloat(e.target.value) })}
                      className="mt-1"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Set to 0 for free</p>
                  </div>
                </div>

                <div>
                  <Label className="mb-2 block">Available Days</Label>
                  <div className="flex flex-wrap gap-2">
                    {dayOptions.map(day => (
                      <Button
                        key={day}
                        type="button"
                        variant={meetGreetSettings.available_days?.includes(day) ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => {
                          const days = meetGreetSettings.available_days || [];
                          if (days.includes(day)) {
                            setMeetGreetSettings({ ...meetGreetSettings, available_days: days.filter(d => d !== day) });
                          } else {
                            setMeetGreetSettings({ ...meetGreetSettings, available_days: [...days, day] });
                          }
                        }}
                      >
                        {day.charAt(0).toUpperCase() + day.slice(1)}
                      </Button>
                    ))}
                  </div>
                </div>

                <div>
                  <Label className="mb-2 block">Available Time Slots</Label>
                  <div className="flex flex-wrap gap-2">
                    {(meetGreetSettings.available_times || []).map((time, idx) => (
                      <div key={idx} className="flex items-center gap-1 bg-muted/30 px-3 py-1 rounded-full">
                        <span>{time}</span>
                        <button
                          type="button"
                          className="text-red-500 hover:text-red-700"
                          onClick={() => setMeetGreetSettings({
                            ...meetGreetSettings,
                            available_times: meetGreetSettings.available_times.filter((_, i) => i !== idx)
                          })}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                    <Input
                      type="time"
                      className="w-32"
                      onChange={(e) => {
                        if (e.target.value && !meetGreetSettings.available_times?.includes(e.target.value)) {
                          setMeetGreetSettings({
                            ...meetGreetSettings,
                            available_times: [...(meetGreetSettings.available_times || []), e.target.value].sort()
                          });
                          e.target.value = '';
                        }
                      }}
                    />
                  </div>
                </div>

                <Button onClick={handleSaveMeetGreetSettings} disabled={saving}>
                  <SaveIcon size={16} className="mr-2" /> {saving ? 'Saving...' : 'Save Meet & Greet Settings'}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Pricing Rule Modal */}
      <Dialog open={pricingModalOpen} onOpenChange={setPricingModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingRule ? 'Edit Pricing Rule' : 'Create Pricing Rule'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Rule Name</Label>
              <Input
                value={ruleForm.name}
                onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                placeholder="e.g., Weekend Surcharge"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Rule Type</Label>
                <select
                  value={ruleForm.rule_type}
                  onChange={(e) => setRuleForm({ ...ruleForm, rule_type: e.target.value })}
                  className="w-full p-2 border rounded-lg mt-1"
                >
                  <option value="weekend">Weekend</option>
                  <option value="holiday">Holiday</option>
                  <option value="seasonal">Seasonal</option>
                  <option value="blackout">Blackout</option>
                </select>
              </div>
              <div>
                <Label>Modifier Type</Label>
                <select
                  value={ruleForm.modifier_type}
                  onChange={(e) => setRuleForm({ ...ruleForm, modifier_type: e.target.value })}
                  className="w-full p-2 border rounded-lg mt-1"
                >
                  <option value="percentage">Percentage</option>
                  <option value="flat">Flat Amount</option>
                </select>
              </div>
            </div>
            <div>
              <Label>Modifier Value</Label>
              <Input
                type="number"
                value={ruleForm.modifier_value}
                onChange={(e) => setRuleForm({ ...ruleForm, modifier_value: parseFloat(e.target.value) })}
              />
            </div>
            {['holiday', 'seasonal', 'blackout'].includes(ruleForm.rule_type) && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={ruleForm.start_date}
                    onChange={(e) => setRuleForm({ ...ruleForm, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={ruleForm.end_date}
                    onChange={(e) => setRuleForm({ ...ruleForm, end_date: e.target.value })}
                  />
                </div>
              </div>
            )}
            <div className="flex items-center gap-2">
              <Switch
                checked={ruleForm.active}
                onCheckedChange={(checked) => setRuleForm({ ...ruleForm, active: checked })}
              />
              <Label>Active</Label>
            </div>
            <div className="flex gap-3 pt-4">
              <Button variant="outline" onClick={() => setPricingModalOpen(false)} className="flex-1">Cancel</Button>
              <Button onClick={handleCreatePricingRule} className="flex-1">{editingRule ? 'Update' : 'Create'}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminSettingsPage;
