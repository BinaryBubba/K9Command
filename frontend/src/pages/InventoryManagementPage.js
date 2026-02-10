import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon, PlusIcon, PackageIcon, AlertTriangleIcon,
  SearchIcon, EditIcon, TrendingDownIcon, RefreshCwIcon, DollarSignIcon
} from 'lucide-react';
import api from '../utils/api';

const CATEGORIES = [
  { value: 'food', label: 'Food' },
  { value: 'treats', label: 'Treats' },
  { value: 'toys', label: 'Toys' },
  { value: 'grooming', label: 'Grooming' },
  { value: 'accessories', label: 'Accessories' },
  { value: 'medication', label: 'Medication' },
  { value: 'other', label: 'Other' }
];

const STATUS_COLORS = {
  in_stock: 'bg-green-500',
  low_stock: 'bg-amber-500',
  out_of_stock: 'bg-red-500',
  discontinued: 'bg-slate-500'
};

export default function InventoryManagementPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [lowStockProducts, setLowStockProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  
  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [adjustQuantity, setAdjustQuantity] = useState(0);
  const [adjustReason, setAdjustReason] = useState('');
  
  // New product form
  const [newProduct, setNewProduct] = useState({
    sku: '', name: '', description: '', category: 'other',
    price_cents: 0, cost_cents: 0, quantity: 0, reorder_point: 5
  });

  useEffect(() => {
    loadProducts();
    loadLowStock();
  }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await api.get('/moego/inventory/products');
      setProducts(res.data.products || []);
    } catch (error) {
      toast.error('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  };

  const loadLowStock = async () => {
    try {
      const res = await api.get('/moego/inventory/low-stock');
      setLowStockProducts(res.data.products || []);
    } catch (error) {
      console.error('Failed to load low stock:', error);
    }
  };

  const handleAddProduct = async () => {
    if (!newProduct.sku || !newProduct.name) {
      toast.error('SKU and name are required');
      return;
    }
    
    try {
      await api.post('/moego/inventory/products', {
        ...newProduct,
        price_cents: Math.round(newProduct.price_cents * 100),
        cost_cents: newProduct.cost_cents ? Math.round(newProduct.cost_cents * 100) : null
      });
      toast.success('Product added');
      setShowAddModal(false);
      setNewProduct({
        sku: '', name: '', description: '', category: 'other',
        price_cents: 0, cost_cents: 0, quantity: 0, reorder_point: 5
      });
      loadProducts();
      loadLowStock();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add product');
    }
  };

  const handleAdjustInventory = async () => {
    if (!selectedProduct || adjustQuantity === 0) {
      toast.error('Please enter a quantity to adjust');
      return;
    }
    
    try {
      await api.post('/moego/inventory/adjust', {
        product_id: selectedProduct.id,
        quantity_change: adjustQuantity,
        reason: adjustReason || 'Manual adjustment'
      });
      toast.success('Inventory adjusted');
      setShowAdjustModal(false);
      setSelectedProduct(null);
      setAdjustQuantity(0);
      setAdjustReason('');
      loadProducts();
      loadLowStock();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to adjust inventory');
    }
  };

  const filteredProducts = products.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         p.sku.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = !filterCategory || p.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  const formatCurrency = (cents) => `$${(cents / 100).toFixed(2)}`;

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="inventory-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" onClick={() => navigate('/admin/dashboard')} className="text-slate-400 hover:text-white">
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Inventory Management</h1>
                <p className="text-slate-400 text-sm">Manage retail products and stock levels</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" onClick={() => { loadProducts(); loadLowStock(); }} className="border-slate-600 text-slate-300">
                <RefreshCwIcon size={16} />
              </Button>
              <Button onClick={() => setShowAddModal(true)} className="bg-blue-600 hover:bg-blue-700">
                <PlusIcon size={16} className="mr-2" />
                Add Product
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Low Stock Alert */}
        {lowStockProducts.length > 0 && (
          <Card className="bg-amber-500/10 border-amber-500/30 mb-6">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangleIcon className="text-amber-400" size={24} />
                <div>
                  <p className="text-white font-semibold">{lowStockProducts.length} Product(s) Need Restocking</p>
                  <p className="text-sm text-slate-400">
                    {lowStockProducts.map(p => p.name).slice(0, 3).join(', ')}
                    {lowStockProducts.length > 3 && ` +${lowStockProducts.length - 3} more`}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                <PackageIcon className="text-blue-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{products.length}</p>
                <p className="text-xs text-slate-400">Total Products</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <DollarSignIcon className="text-green-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {formatCurrency(products.reduce((sum, p) => sum + (p.price_cents * p.quantity), 0))}
                </p>
                <p className="text-xs text-slate-400">Inventory Value</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                <TrendingDownIcon className="text-amber-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{lowStockProducts.length}</p>
                <p className="text-xs text-slate-400">Low Stock</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                <PackageIcon className="text-red-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {products.filter(p => p.status === 'out_of_stock').length}
                </p>
                <p className="text-xs text-slate-400">Out of Stock</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <Input
              placeholder="Search by name or SKU..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-slate-800 border-slate-700 text-white"
            />
          </div>
          <Select value={filterCategory || 'all'} onValueChange={(v) => setFilterCategory(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {CATEGORIES.map(cat => (
                <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Products Table */}
        <Card className="bg-slate-900 border-slate-700">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left p-4 text-slate-400 font-medium">SKU</th>
                  <th className="text-left p-4 text-slate-400 font-medium">Product</th>
                  <th className="text-left p-4 text-slate-400 font-medium">Category</th>
                  <th className="text-right p-4 text-slate-400 font-medium">Price</th>
                  <th className="text-right p-4 text-slate-400 font-medium">Stock</th>
                  <th className="text-center p-4 text-slate-400 font-medium">Status</th>
                  <th className="text-right p-4 text-slate-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">
                      No products found
                    </td>
                  </tr>
                ) : (
                  filteredProducts.map(product => (
                    <tr key={product.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                      <td className="p-4 text-slate-300 font-mono text-sm">{product.sku}</td>
                      <td className="p-4">
                        <p className="text-white font-medium">{product.name}</p>
                        {product.description && (
                          <p className="text-xs text-slate-500 truncate max-w-xs">{product.description}</p>
                        )}
                      </td>
                      <td className="p-4">
                        <Badge className="bg-slate-700 text-slate-300 capitalize">{product.category}</Badge>
                      </td>
                      <td className="p-4 text-right text-white">{formatCurrency(product.price_cents)}</td>
                      <td className="p-4 text-right">
                        <span className={`font-semibold ${product.quantity <= product.reorder_point ? 'text-amber-400' : 'text-white'}`}>
                          {product.quantity}
                        </span>
                      </td>
                      <td className="p-4 text-center">
                        <Badge className={`${STATUS_COLORS[product.status]} text-white capitalize`}>
                          {product.status.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="p-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => { setSelectedProduct(product); setShowAdjustModal(true); }}
                          className="text-slate-400 hover:text-white"
                        >
                          <EditIcon size={16} />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </main>

      {/* Add Product Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Add New Product</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">SKU *</Label>
                <Input
                  value={newProduct.sku}
                  onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value.toUpperCase() })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="PROD-001"
                />
              </div>
              <div>
                <Label className="text-slate-300">Category</Label>
                <Select value={newProduct.category} onValueChange={(v) => setNewProduct({ ...newProduct, category: v })}>
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(cat => (
                      <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-slate-300">Product Name *</Label>
              <Input
                value={newProduct.name}
                onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white mt-1"
                placeholder="Premium Dog Food"
              />
            </div>
            <div>
              <Label className="text-slate-300">Description</Label>
              <Textarea
                value={newProduct.description}
                onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white mt-1"
                placeholder="Optional description..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Price ($)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={newProduct.price_cents}
                  onChange={(e) => setNewProduct({ ...newProduct, price_cents: parseFloat(e.target.value) || 0 })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                />
              </div>
              <div>
                <Label className="text-slate-300">Cost ($)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={newProduct.cost_cents}
                  onChange={(e) => setNewProduct({ ...newProduct, cost_cents: parseFloat(e.target.value) || 0 })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Initial Quantity</Label>
                <Input
                  type="number"
                  value={newProduct.quantity}
                  onChange={(e) => setNewProduct({ ...newProduct, quantity: parseInt(e.target.value) || 0 })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                />
              </div>
              <div>
                <Label className="text-slate-300">Reorder Point</Label>
                <Input
                  type="number"
                  value={newProduct.reorder_point}
                  onChange={(e) => setNewProduct({ ...newProduct, reorder_point: parseInt(e.target.value) || 5 })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddModal(false)} className="border-slate-600 text-slate-300">Cancel</Button>
            <Button onClick={handleAddProduct} className="bg-blue-600 hover:bg-blue-700">Add Product</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Adjust Inventory Modal */}
      <Dialog open={showAdjustModal} onOpenChange={setShowAdjustModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Adjust Inventory</DialogTitle>
          </DialogHeader>
          {selectedProduct && (
            <div className="space-y-4 py-4">
              <div className="bg-slate-800 rounded-lg p-4">
                <p className="text-slate-400 text-sm">Product</p>
                <p className="text-white font-medium">{selectedProduct.name}</p>
                <p className="text-slate-500 text-sm">Current Stock: {selectedProduct.quantity}</p>
              </div>
              <div>
                <Label className="text-slate-300">Quantity Change</Label>
                <Input
                  type="number"
                  value={adjustQuantity}
                  onChange={(e) => setAdjustQuantity(parseInt(e.target.value) || 0)}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="+ to add, - to remove"
                />
                <p className="text-xs text-slate-500 mt-1">
                  New quantity: {selectedProduct.quantity + adjustQuantity}
                </p>
              </div>
              <div>
                <Label className="text-slate-300">Reason</Label>
                <Input
                  value={adjustReason}
                  onChange={(e) => setAdjustReason(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="e.g., Restock, Damaged, Sold"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAdjustModal(false)} className="border-slate-600 text-slate-300">Cancel</Button>
            <Button onClick={handleAdjustInventory} className="bg-blue-600 hover:bg-blue-700">Adjust</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
