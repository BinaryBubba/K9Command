import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { ArrowLeftIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const AddDogPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    breed: '',
    age: '',
    weight: '',
    gender: 'male',
    color: '',
    birthday: '',
    meal_routine: '',
    medication_requirements: '',
    allergies: '',
    friendly_to_cats: false,
    friendly_with_dogs: true,
    seizure_activity: false,
    afraid_of_thunder: false,
    afraid_of_fireworks: false,
    resource_guarding: false,
    fence_aggression: false,
    incidents_of_aggression: '',
    other_notes: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        age: formData.age ? parseInt(formData.age) : null,
        weight: formData.weight ? parseFloat(formData.weight) : null,
        birthday: formData.birthday || null,
      };

      const response = await api.post('/dogs', payload);
      const dogId = response.data.id;
      
      // Upload photo if provided
      if (photoFile) {
        const photoFormData = new FormData();
        photoFormData.append('file', photoFile);
        await api.post(`/dogs/${dogId}/upload-photo`, photoFormData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }

      toast.success(`${formData.name} has been added successfully!`);
      navigate('/customer/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add dog');
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setPhotoFile(file);
      setPhotoPreview(URL.createObjectURL(file));
    }
  };

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 md:px-8 py-4">
          <Button
            data-testid="back-button"
            variant="ghost"
            onClick={() => navigate('/customer/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Add a New Dog</h1>
          <p className="text-muted-foreground mt-1">Tell us all about your furry friend</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-8 py-8">
        <form onSubmit={handleSubmit}>
          {/* Basic Information */}
          <Card data-testid="basic-info-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {/* Photo Upload */}
              <div className="mb-6">
                <Label htmlFor="photo">Dog Photo</Label>
                <div className="mt-2 flex items-center gap-4">
                  {photoPreview ? (
                    <img
                      src={photoPreview}
                      alt="Dog preview"
                      className="w-24 h-24 rounded-full object-cover border-2 border-primary"
                    />
                  ) : (
                    <div className="w-24 h-24 rounded-full bg-muted flex items-center justify-center border-2 border-dashed border-border">
                      <DogIcon size={32} className="text-muted-foreground" />
                    </div>
                  )}
                  <div>
                    <Input
                      id="photo"
                      data-testid="dog-photo-input"
                      type="file"
                      accept="image/*"
                      onChange={handlePhotoChange}
                      className="max-w-xs"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Upload a photo of your dog</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    data-testid="dog-name-input"
                    value={formData.name}
                    onChange={(e) => handleChange('name', e.target.value)}
                    required
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="breed">Breed *</Label>
                  <Input
                    id="breed"
                    data-testid="dog-breed-input"
                    value={formData.breed}
                    onChange={(e) => handleChange('breed', e.target.value)}
                    required
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="gender">Gender</Label>
                  <select
                    id="gender"
                    data-testid="dog-gender-select"
                    value={formData.gender}
                    onChange={(e) => handleChange('gender', e.target.value)}
                    className="w-full mt-1 p-2 border rounded-xl"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                  </select>
                </div>
                <div>
                  <Label htmlFor="age">Age (years)</Label>
                  <Input
                    id="age"
                    data-testid="dog-age-input"
                    type="number"
                    value={formData.age}
                    onChange={(e) => handleChange('age', e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="weight">Weight (lbs)</Label>
                  <Input
                    id="weight"
                    data-testid="dog-weight-input"
                    type="number"
                    step="0.1"
                    value={formData.weight}
                    onChange={(e) => handleChange('weight', e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="color">Color</Label>
                  <Input
                    id="color"
                    data-testid="dog-color-input"
                    value={formData.color}
                    onChange={(e) => handleChange('color', e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="birthday">Birthday</Label>
                  <Input
                    id="birthday"
                    data-testid="dog-birthday-input"
                    type="date"
                    value={formData.birthday}
                    onChange={(e) => handleChange('birthday', e.target.value)}
                    className="mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Medical & Care */}
          <Card data-testid="medical-care-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">Medical & Care Information</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div>
                <Label htmlFor="meal_routine">Meal Routine</Label>
                <Textarea
                  id="meal_routine"
                  data-testid="dog-meal-routine-input"
                  value={formData.meal_routine}
                  onChange={(e) => handleChange('meal_routine', e.target.value)}
                  placeholder="E.g., 2 cups dry food, twice daily"
                  className="mt-1"
                  rows={3}
                />
              </div>
              <div>
                <Label htmlFor="medication_requirements">Medication Requirements</Label>
                <Textarea
                  id="medication_requirements"
                  data-testid="dog-medication-input"
                  value={formData.medication_requirements}
                  onChange={(e) => handleChange('medication_requirements', e.target.value)}
                  placeholder="List any medications and dosage"
                  className="mt-1"
                  rows={3}
                />
              </div>
              <div>
                <Label htmlFor="allergies">Allergies</Label>
                <Textarea
                  id="allergies"
                  data-testid="dog-allergies-input"
                  value={formData.allergies}
                  onChange={(e) => handleChange('allergies', e.target.value)}
                  placeholder="Food, environmental, or medication allergies"
                  className="mt-1"
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          {/* Behavior & Temperament */}
          <Card data-testid="behavior-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">Behavior & Temperament</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="friendly_to_cats"
                    data-testid="dog-friendly-cats-checkbox"
                    checked={formData.friendly_to_cats}
                    onCheckedChange={(checked) => handleChange('friendly_to_cats', checked)}
                  />
                  <Label htmlFor="friendly_to_cats" className="cursor-pointer">Friendly to Cats</Label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="friendly_with_dogs"
                    data-testid="dog-friendly-dogs-checkbox"
                    checked={formData.friendly_with_dogs}
                    onCheckedChange={(checked) => handleChange('friendly_with_dogs', checked)}
                  />
                  <Label htmlFor="friendly_with_dogs" className="cursor-pointer">Friendly with Dogs</Label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="seizure_activity"
                    data-testid="dog-seizure-checkbox"
                    checked={formData.seizure_activity}
                    onCheckedChange={(checked) => handleChange('seizure_activity', checked)}
                  />
                  <Label htmlFor="seizure_activity" className="cursor-pointer">Seizure Activity</Label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="afraid_of_thunder"
                    data-testid="dog-thunder-checkbox"
                    checked={formData.afraid_of_thunder}
                    onCheckedChange={(checked) => handleChange('afraid_of_thunder', checked)}
                  />
                  <Label htmlFor="afraid_of_thunder" className="cursor-pointer">Afraid of Thunder</Label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="afraid_of_fireworks"
                    data-testid="dog-fireworks-checkbox"
                    checked={formData.afraid_of_fireworks}
                    onCheckedChange={(checked) => handleChange('afraid_of_fireworks', checked)}
                  />
                  <Label htmlFor="afraid_of_fireworks" className="cursor-pointer">Afraid of Fireworks</Label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="resource_guarding"
                    data-testid="dog-resource-guarding-checkbox"
                    checked={formData.resource_guarding}
                    onCheckedChange={(checked) => handleChange('resource_guarding', checked)}
                  />
                  <Label htmlFor="resource_guarding" className="cursor-pointer">Resource Guarding</Label>
                </div>
                <div className="flex items-center space-x-3">
                  <Checkbox
                    id="fence_aggression"
                    data-testid="dog-fence-aggression-checkbox"
                    checked={formData.fence_aggression}
                    onCheckedChange={(checked) => handleChange('fence_aggression', checked)}
                  />
                  <Label htmlFor="fence_aggression" className="cursor-pointer">Fence Aggression</Label>
                </div>
              </div>
              <div className="mt-6">
                <Label htmlFor="incidents_of_aggression">Incidents of Aggression</Label>
                <Textarea
                  id="incidents_of_aggression"
                  data-testid="dog-aggression-input"
                  value={formData.incidents_of_aggression}
                  onChange={(e) => handleChange('incidents_of_aggression', e.target.value)}
                  placeholder="Please describe any aggressive incidents"
                  className="mt-1"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Additional Notes */}
          <Card data-testid="notes-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">Additional Notes</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <Textarea
                id="other_notes"
                data-testid="dog-other-notes-input"
                value={formData.other_notes}
                onChange={(e) => handleChange('other_notes', e.target.value)}
                placeholder="Any other important information we should know"
                rows={4}
              />
            </CardContent>
          </Card>

          {/* Submit Button */}
          <div className="flex gap-4 justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/customer/dashboard')}
              className="rounded-full px-8"
            >
              Cancel
            </Button>
            <Button
              data-testid="submit-dog-button"
              type="submit"
              disabled={loading}
              className="rounded-full px-8 py-6 text-lg font-semibold"
            >
              {loading ? 'Adding...' : 'Add Dog'}
            </Button>
          </div>
        </form>
      </main>
    </div>
  );
};

export default AddDogPage;
