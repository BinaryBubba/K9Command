import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { 
  PlusIcon, 
  TagIcon,
  PercentIcon,
  DollarSignIcon,
  CalendarIcon,
  UsersIcon,
  CopyIcon,
  EditIcon,
  TrashIcon,
  ArrowLeftIcon,
  GiftIcon,
  CheckCircleIcon,
  XCircleIcon
} from 'lucide-react';
import api from '../utils/api';

const DISCOUNT_TYPES = [
  { value: 'percentage', label: 'Percentage Off', icon: PercentIcon },
  { value: 'flat_amount', label: 'Fixed Amount', icon: DollarSignIcon },
  { value: 'free_night', label: 'Free Night', icon: GiftIcon },
  { value: 'free_addon', label: 'Free Add-On', icon: GiftIcon },
];

export default function CouponManagementPage() {
  const navigate = useNavigate();
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    discount_type: 'percentage',
    discount_value: '',
    max_uses: '',
    max_uses_per_customer: 1,
    min_order_amount: '',
    min_nights: '',
    first_booking_only: false,
    valid_from: '',
    valid_until: '',
  });

  useEffect(() => {
    loadCoupons();
  }, []);

  const loadCoupons = async () => {
    setLoading(true);
    try {
      const response = await api.get('/k9/coupons');
      setCoupons(response.data);
    } catch (error) {
      toast.error('Failed to load coupons');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCoupon = async () => {
    if (!formData.code.trim() || !formData.name.trim()) {
      toast.error('Please enter a code and name');
      return;
    }
    if (!formData.discount_value) {
      toast.error('Please enter a discount value');
      return;
    }

    try {
      const payload = {
        ...formData,
        discount_value: parseFloat(formData.discount_value),
        max_uses: formData.max_uses ? parseInt(formData.max_uses) : null,
        max_uses_per_customer: parseInt(formData.max_uses_per_customer) || 1,
        min_order_amount: formData.min_order_amount ? parseFloat(formData.min_order_amount) : null,
        min_nights: formData.min_nights ? parseInt(formData.min_nights) : null,
        valid_from: formData.valid_from || null,
        valid_until: formData.valid_until || null,
      };

      if (editingCoupon) {
        await api.patch(`/k9/coupons/${editingCoupon.id}`, payload);
        toast.success('Coupon updated');
      } else {
        await api.post('/k9/coupons', payload);
        toast.success('Coupon created');
      }
      
      setShowCreateModal(false);
      setEditingCoupon(null);
      resetForm();
      loadCoupons();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save coupon');
    }
  };

  const handleDeleteCoupon = async (couponId) => {
    if (!window.confirm('Are you sure you want to deactivate this coupon?')) return;
    
    try {
      await api.delete(`/k9/coupons/${couponId}`);
      toast.success('Coupon deactivated');
      loadCoupons();
    } catch (error) {
      toast.error('Failed to delete coupon');
    }
  };

  const handleEditCoupon = (coupon) => {
    setEditingCoupon(coupon);
    setFormData({
      code: coupon.code,
      name: coupon.name,
      description: coupon.description || '',
      discount_type: coupon.discount_type,
      discount_value: coupon.discount_value?.toString() || '',
      max_uses: coupon.max_uses?.toString() || '',
      max_uses_per_customer: coupon.max_uses_per_customer || 1,
      min_order_amount: coupon.min_order_amount?.toString() || '',
      min_nights: coupon.min_nights?.toString() || '',
      first_booking_only: coupon.first_booking_only || false,
      valid_from: coupon.valid_from?.split('T')[0] || '',
      valid_until: coupon.valid_until?.split('T')[0] || '',
    });
    setShowCreateModal(true);
  };

  const copyCode = (code) => {
    navigator.clipboard.writeText(code);
    toast.success('Code copied to clipboard');
  };

  const resetForm = () => {
    setFormData({
      code: '',
      name: '',
      description: '',
      discount_type: 'percentage',
      discount_value: '',
      max_uses: '',
      max_uses_per_customer: 1,
      min_order_amount: '',
      min_nights: '',
      first_booking_only: false,
      valid_from: '',
      valid_until: '',
    });
  };

  const formatDiscount = (coupon) => {
    switch (coupon.discount_type) {
      case 'percentage':
        return `${coupon.discount_value}% off`;
      case 'flat_amount':
        return `$${coupon.discount_value} off`;
      case 'free_night':
        return `Buy ${coupon.buy_nights_get_free || 'X'}, get 1 free`;
      case 'free_addon':
        return 'Free add-on';
      default:
        return coupon.discount_value;
    }
  };

  const isExpired = (coupon) => {
    if (!coupon.valid_until) return false;
    return new Date(coupon.valid_until) < new Date();
  };

  const isNotYetValid = (coupon) => {
    if (!coupon.valid_from) return false;
    return new Date(coupon.valid_from) > new Date();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="coupon-management-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/admin')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Coupon Codes</h1>
                <p className="text-slate-400 text-sm">Manage discount codes</p>
              </div>
            </div>
            <Button
              onClick={() => { resetForm(); setShowCreateModal(true); }}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              data-testid="add-coupon-btn"
            >
              <PlusIcon size={18} className="mr-2" />
              Create Coupon
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-blue-600 to-blue-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <TagIcon className="text-white" size={24} />
                <div>
                  <p className="text-blue-100 text-sm">Total Coupons</p>
                  <p className="text-2xl font-bold text-white">{coupons.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-600 to-green-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <CheckCircleIcon className="text-white" size={24} />
                <div>
                  <p className="text-green-100 text-sm">Active</p>
                  <p className="text-2xl font-bold text-white">
                    {coupons.filter(c => !isExpired(c) && !isNotYetValid(c)).length}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-600 to-amber-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <UsersIcon className="text-white" size={24} />
                <div>
                  <p className="text-amber-100 text-sm">Total Uses</p>
                  <p className="text-2xl font-bold text-white">
                    {coupons.reduce((sum, c) => sum + (c.current_uses || 0), 0)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-red-600 to-red-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <XCircleIcon className="text-white" size={24} />
                <div>
                  <p className="text-red-100 text-sm">Expired</p>
                  <p className="text-2xl font-bold text-white">
                    {coupons.filter(isExpired).length}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Coupons List */}
        {coupons.length === 0 ? (
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="py-12 text-center">
              <TagIcon className="mx-auto text-slate-600 mb-4" size={48} />
              <h3 className="text-lg font-semibold text-slate-400 mb-2">No coupons yet</h3>
              <p className="text-slate-500 mb-4">Create your first coupon code</p>
              <Button onClick={() => setShowCreateModal(true)} className="bg-blue-600 hover:bg-blue-700">
                <PlusIcon size={16} className="mr-2" />
                Create Coupon
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {coupons.map(coupon => (
              <Card 
                key={coupon.id}
                className={`bg-slate-900 border-slate-700 ${isExpired(coupon) ? 'opacity-60' : ''}`}
                data-testid={`coupon-card-${coupon.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <code className="px-2 py-1 bg-slate-800 rounded text-green-400 font-mono font-bold">
                          {coupon.code}
                        </code>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyCode(coupon.code)}
                          className="h-7 w-7 p-0 text-slate-400 hover:text-white"
                        >
                          <CopyIcon size={14} />
                        </Button>
                      </div>
                      <h3 className="font-medium text-white mt-2">{coupon.name}</h3>
                    </div>
                    {isExpired(coupon) ? (
                      <Badge className="bg-red-500/20 text-red-400">Expired</Badge>
                    ) : isNotYetValid(coupon) ? (
                      <Badge className="bg-amber-500/20 text-amber-400">Scheduled</Badge>
                    ) : (
                      <Badge className="bg-green-500/20 text-green-400">Active</Badge>
                    )}
                  </div>

                  <p className="text-2xl font-bold text-white mb-2">
                    {formatDiscount(coupon)}
                  </p>

                  {coupon.description && (
                    <p className="text-slate-400 text-sm mb-3">{coupon.description}</p>
                  )}

                  <div className="space-y-1 text-sm text-slate-400 mb-4">
                    {coupon.max_uses && (
                      <p>Uses: {coupon.current_uses || 0} / {coupon.max_uses}</p>
                    )}
                    {coupon.min_order_amount && (
                      <p>Min order: ${coupon.min_order_amount}</p>
                    )}
                    {coupon.min_nights && (
                      <p>Min nights: {coupon.min_nights}</p>
                    )}
                    {coupon.first_booking_only && (
                      <Badge variant="outline" className="border-slate-600">First booking only</Badge>
                    )}
                  </div>

                  {(coupon.valid_from || coupon.valid_until) && (
                    <div className="flex items-center gap-2 text-xs text-slate-500 mb-4">
                      <CalendarIcon size={12} />
                      <span>
                        {coupon.valid_from && new Date(coupon.valid_from).toLocaleDateString()}
                        {coupon.valid_from && coupon.valid_until && ' - '}
                        {coupon.valid_until && new Date(coupon.valid_until).toLocaleDateString()}
                      </span>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditCoupon(coupon)}
                      className="flex-1 border-slate-600 text-slate-300"
                    >
                      <EditIcon size={14} className="mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteCoupon(coupon.id)}
                      className="text-slate-400 hover:text-red-400"
                    >
                      <TrashIcon size={14} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Create/Edit Modal */}
      <Dialog open={showCreateModal} onOpenChange={(open) => { setShowCreateModal(open); if (!open) setEditingCoupon(null); }}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white">
              {editingCoupon ? 'Edit Coupon' : 'Create Coupon'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Code</Label>
                <Input
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="SUMMER20"
                  className="mt-1 bg-slate-800 border-slate-600 text-white font-mono"
                />
              </div>
              <div>
                <Label className="text-slate-300">Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Summer Sale"
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
            </div>

            <div>
              <Label className="text-slate-300">Description</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="20% off summer bookings"
                className="mt-1 bg-slate-800 border-slate-600 text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Discount Type</Label>
                <Select value={formData.discount_type} onValueChange={(v) => setFormData({ ...formData, discount_type: v })}>
                  <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DISCOUNT_TYPES.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-slate-300">
                  {formData.discount_type === 'percentage' ? 'Percentage' : 'Amount'}
                </Label>
                <Input
                  type="number"
                  value={formData.discount_value}
                  onChange={(e) => setFormData({ ...formData, discount_value: e.target.value })}
                  placeholder={formData.discount_type === 'percentage' ? '20' : '50'}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Max Uses (Total)</Label>
                <Input
                  type="number"
                  value={formData.max_uses}
                  onChange={(e) => setFormData({ ...formData, max_uses: e.target.value })}
                  placeholder="Unlimited"
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
              <div>
                <Label className="text-slate-300">Per Customer</Label>
                <Input
                  type="number"
                  value={formData.max_uses_per_customer}
                  onChange={(e) => setFormData({ ...formData, max_uses_per_customer: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Min Order Amount ($)</Label>
                <Input
                  type="number"
                  value={formData.min_order_amount}
                  onChange={(e) => setFormData({ ...formData, min_order_amount: e.target.value })}
                  placeholder="No minimum"
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
              <div>
                <Label className="text-slate-300">Min Nights</Label>
                <Input
                  type="number"
                  value={formData.min_nights}
                  onChange={(e) => setFormData({ ...formData, min_nights: e.target.value })}
                  placeholder="No minimum"
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Valid From</Label>
                <Input
                  type="date"
                  value={formData.valid_from}
                  onChange={(e) => setFormData({ ...formData, valid_from: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
              <div>
                <Label className="text-slate-300">Valid Until</Label>
                <Input
                  type="date"
                  value={formData.valid_until}
                  onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div>
                <Label className="text-slate-300">First Booking Only</Label>
                <p className="text-xs text-slate-500">Only new customers can use</p>
              </div>
              <Switch 
                checked={formData.first_booking_only} 
                onCheckedChange={(v) => setFormData({ ...formData, first_booking_only: v })} 
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleCreateCoupon} className="bg-blue-600 hover:bg-blue-700">
              {editingCoupon ? 'Update' : 'Create'} Coupon
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
