import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { ArrowLeftIcon, SearchIcon, DogIcon, MailIcon, PhoneIcon, UserIcon, PlusIcon, EditIcon, TrashIcon, CheckIcon, XIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminCustomersPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [customers, setCustomers] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    is_active: true,
    notes: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
    emergency_contact: '',
    emergency_phone: '',
  });

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [usersRes, dogsRes] = await Promise.all([
        api.get('/admin/users?role=customer'),
        api.get('/dogs'),
      ]);
      setCustomers(usersRes.data);
      setDogs(dogsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (customerId, currentStatus) => {
    try {
      await api.patch(`/admin/users/${customerId}/status?is_active=${!currentStatus}`);
      toast.success(`Customer ${currentStatus ? 'deactivated' : 'activated'}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update customer status');
    }
  };

  const openCreateModal = () => {
    setEditMode(false);
    setSelectedCustomer(null);
    setFormData({ full_name: '', email: '', phone: '', password: '', is_active: true, notes: '', address: '', city: '', state: '', zip_code: '', emergency_contact: '', emergency_phone: '' });
    setModalOpen(true);
  };

  const openEditModal = (customer) => {
    setEditMode(true);
    setSelectedCustomer(customer);
    setFormData({
      full_name: customer.full_name || '',
      email: customer.email || '',
      phone: customer.phone || '',
      password: '',
      is_active: customer.is_active !== false,
      notes: customer.notes || '',
      address: customer.address || '',
      city: customer.city || '',
      state: customer.state || '',
      zip_code: customer.zip_code || '',
      emergency_contact: customer.emergency_contact || '',
      emergency_phone: customer.emergency_phone || '',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editMode) {
        await api.patch(`/admin/customers/${selectedCustomer.id}`, formData);
        toast.success('Customer updated');
      } else {
        const result = await api.post('/admin/customers', formData);
        toast.success(`Customer created! Temp password: ${result.data.temp_password}`);
      }
      setModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save customer');
    }
  };

  const handleDelete = async (customerId) => {
    if (!window.confirm('Are you sure you want to deactivate this customer?')) return;
    try {
      await api.delete(`/admin/customers/${customerId}`);
      toast.success('Customer deactivated');
      fetchData();
    } catch (error) {
      toast.error('Failed to deactivate customer');
    }
  };

  const filteredCustomers = customers.filter((customer) =>
    customer.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    customer.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getDogsByHousehold = (householdId) => {
    return dogs.filter(dog => dog.household_id === householdId);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Customer Management</h1>
              <p className="text-muted-foreground mt-1">View and manage all customers and their dogs</p>
            </div>
            <Button onClick={openCreateModal} className="rounded-full">
              <PlusIcon size={18} className="mr-2" /> Add Customer
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Search */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
              <Input placeholder="Search by name or email..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Total Customers</p>
              <p className="text-3xl font-serif font-bold text-primary">{customers.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Active Customers</p>
              <p className="text-3xl font-serif font-bold text-green-600">{customers.filter(c => c.is_active !== false).length}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Total Dogs</p>
              <p className="text-3xl font-serif font-bold text-secondary-foreground">{dogs.length}</p>
            </CardContent>
          </Card>
        </div>

        {/* Customers List */}
        <div className="space-y-4">
          {filteredCustomers.length === 0 ? (
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardContent className="p-12 text-center">
                <UserIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No customers found</p>
              </CardContent>
            </Card>
          ) : (
            filteredCustomers.map((customer) => {
              const customerDogs = getDogsByHousehold(customer.household_id);
              return (
                <Card key={customer.id} className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardContent className="p-6">
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <UserIcon className="text-primary" size={20} />
                          </div>
                          <div>
                            <h3 className="text-lg font-semibold">{customer.full_name || 'Unknown'}</h3>
                            <p className="text-sm text-muted-foreground flex items-center gap-1">
                              <MailIcon size={14} /> {customer.email}
                            </p>
                            {customer.phone && (
                              <p className="text-sm text-muted-foreground flex items-center gap-1">
                                <PhoneIcon size={14} /> {customer.phone}
                              </p>
                            )}
                          </div>
                        </div>
                        
                        {customerDogs.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-border">
                            <p className="text-sm font-medium mb-2">Dogs ({customerDogs.length})</p>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                              {customerDogs.map((dog) => (
                                <div key={dog.id} className="p-2 rounded-lg bg-muted/30 border border-border text-sm">
                                  <div className="flex items-center gap-2">
                                    <DogIcon size={14} className="text-muted-foreground" />
                                    <span className="font-medium">{dog.name}</span>
                                  </div>
                                  <p className="text-xs text-muted-foreground">{dog.breed}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      <div className="flex flex-col items-end gap-2">
                        <Badge className={customer.is_active !== false ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {customer.is_active !== false ? 'Active' : 'Inactive'}
                        </Badge>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" onClick={() => openEditModal(customer)}>
                            <EditIcon size={14} className="mr-1" /> Edit
                          </Button>
                          <Button
                            variant={customer.is_active !== false ? 'destructive' : 'default'}
                            size="sm"
                            onClick={() => handleToggleStatus(customer.id, customer.is_active !== false)}
                          >
                            {customer.is_active !== false ? <XIcon size={14} /> : <CheckIcon size={14} />}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      </main>

      {/* Create/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editMode ? 'Edit Customer' : 'Add New Customer'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Full Name *</Label>
                <Input value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} required />
              </div>
              <div>
                <Label>Email *</Label>
                <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required disabled={editMode} />
              </div>
              <div>
                <Label>Phone</Label>
                <Input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} />
              </div>
            </div>
            
            <div className="border-t pt-4">
              <p className="text-sm font-medium mb-3">Address Information</p>
              <div className="space-y-3">
                <div>
                  <Label>Street Address</Label>
                  <Input value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} placeholder="123 Main St" />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <Label>City</Label>
                    <Input value={formData.city} onChange={(e) => setFormData({ ...formData, city: e.target.value })} />
                  </div>
                  <div>
                    <Label>State</Label>
                    <Input value={formData.state} onChange={(e) => setFormData({ ...formData, state: e.target.value })} placeholder="CA" />
                  </div>
                  <div>
                    <Label>Zip Code</Label>
                    <Input value={formData.zip_code} onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })} />
                  </div>
                </div>
              </div>
            </div>
            
            <div className="border-t pt-4">
              <p className="text-sm font-medium mb-3">Emergency Contact</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Contact Name</Label>
                  <Input value={formData.emergency_contact} onChange={(e) => setFormData({ ...formData, emergency_contact: e.target.value })} />
                </div>
                <div>
                  <Label>Contact Phone</Label>
                  <Input value={formData.emergency_phone} onChange={(e) => setFormData({ ...formData, emergency_phone: e.target.value })} />
                </div>
              </div>
            </div>
            
            <div className="border-t pt-4">
              <div>
                <Label>{editMode ? 'New Password (leave blank to keep current)' : 'Password *'}</Label>
                <Input type="password" value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} required={!editMode} />
              </div>
              <div className="mt-3">
                <Label>Notes</Label>
                <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} className="w-full p-2 border rounded-lg" rows={2} />
              </div>
            </div>
            
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)} className="flex-1">Cancel</Button>
              <Button type="submit" className="flex-1">{editMode ? 'Update' : 'Create'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminCustomersPage;
