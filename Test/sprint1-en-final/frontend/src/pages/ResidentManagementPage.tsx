import { useEffect, useState } from 'react';
import {
  createResident,
  deleteResident,
  fetchResidentManagementList,
  ResidentDetail,
  ResidentPayload,
  transferResident,
  updateResident,
} from '../api/client';

const emptyForm: ResidentPayload = {
  id: '',
  name: '',
  medical_history: '',
  daily_habits: '',
  care_notes: '',
  monitoring_status: 'ACTIVE',
  room_number: '',
  building: '',
  floor_level: '',
  location_notes: '',
};

function toForm(resident: ResidentDetail): ResidentPayload {
  return {
    id: resident.id,
    name: resident.name,
    medical_history: resident.medical_history ?? '',
    daily_habits: resident.daily_habits ?? '',
    care_notes: resident.care_notes ?? '',
    monitoring_status: resident.monitoring_status,
    room_number: resident.room_number ?? '',
    building: resident.building ?? '',
    floor_level: resident.floor_level ?? '',
    location_notes: resident.location_notes ?? '',
  };
}

export default function ResidentManagementPage() {
  const [residents, setResidents] = useState<ResidentDetail[]>([]);
  const [form, setForm] = useState<ResidentPayload>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [transferDestination, setTransferDestination] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    fetchResidentManagementList()
      .then(setResidents)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const updateField = (key: keyof ResidentPayload, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const reset = () => {
    setForm(emptyForm);
    setEditingId(null);
    setTransferDestination('');
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');
    if (editingId) {
      const { id: _id, ...payload } = form;
      await updateResident(editingId, payload);
      setMessage(`Updated ${editingId}`);
    } else {
      await createResident(form);
      setMessage(`Registered ${form.id}`);
    }
    reset();
    load();
  };

  const startEdit = (resident: ResidentDetail) => {
    setForm(toForm(resident));
    setEditingId(resident.id);
    setTransferDestination(resident.transfer_destination ?? '');
  };

  const transfer = async () => {
    if (!editingId || !transferDestination.trim()) return;
    await transferResident(editingId, {
      transfer_destination: transferDestination.trim(),
      transfer_date: new Date().toISOString().slice(0, 10),
      location_notes: form.location_notes ?? undefined,
    });
    setMessage(`${editingId} transferred and monitoring paused`);
    reset();
    load();
  };

  const remove = async (residentId: string) => {
    await deleteResident(residentId);
    setMessage(`${residentId} removed from active management; history retained`);
    if (editingId === residentId) reset();
    load();
  };

  if (loading) return <p className="loading">Loading residents...</p>;

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>Resident Management</h1>
      {message && <p className="disclaimer" style={{ background: '#dcfce7', borderColor: '#86efac', color: '#166534' }}>{message}</p>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 16, alignItems: 'start' }}>
        <div className="card" style={{ padding: 0 }}>
          {residents.map((r) => (
            <div key={r.id} style={{ padding: 16, borderBottom: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                <div>
                  <h3>{r.name}</h3>
                  <p style={{ fontSize: 13, color: '#64748b' }}>
                    {r.id} | {r.monitoring_status} | {r.building || '-'} {r.floor_level ? `Floor ${r.floor_level}` : ''} {r.room_number ? `Room ${r.room_number}` : ''}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn-secondary" onClick={() => startEdit(r)}>Edit</button>
                  <button className="btn-secondary" onClick={() => remove(r.id)}>Delete</button>
                </div>
              </div>
              <p style={{ marginTop: 8, fontSize: 13, color: '#475569' }}>
                <strong>Habits:</strong> {r.daily_habits || 'No daily habits recorded'}
              </p>
              {r.transfer_destination && (
                <p style={{ marginTop: 4, fontSize: 13, color: '#92400e' }}>
                  Transferred to {r.transfer_destination} on {r.transfer_date || 'unspecified date'}
                </p>
              )}
            </div>
          ))}
          {residents.length === 0 && <p className="loading">No active residents</p>}
        </div>

        <form className="card" onSubmit={save}>
          <h3 style={{ marginBottom: 12 }}>{editingId ? `Edit ${editingId}` : 'Register New Resident'}</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            <label>
              <span className="form-label">Resident ID</span>
              <input value={form.id} disabled={!!editingId} onChange={(e) => updateField('id', e.target.value)} required />
            </label>
            <label>
              <span className="form-label">Name</span>
              <input value={form.name} onChange={(e) => updateField('name', e.target.value)} required />
            </label>
            <label>
              <span className="form-label">Monitoring Status</span>
              <select value={form.monitoring_status} onChange={(e) => updateField('monitoring_status', e.target.value)}>
                <option value="ACTIVE">Active</option>
                <option value="PAUSED">Paused</option>
              </select>
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
              <label>
                <span className="form-label">Building</span>
                <input value={form.building ?? ''} onChange={(e) => updateField('building', e.target.value)} />
              </label>
              <label>
                <span className="form-label">Floor</span>
                <input value={form.floor_level ?? ''} onChange={(e) => updateField('floor_level', e.target.value)} />
              </label>
              <label>
                <span className="form-label">Room</span>
                <input value={form.room_number ?? ''} onChange={(e) => updateField('room_number', e.target.value)} />
              </label>
            </div>
            <label>
              <span className="form-label">Medical History</span>
              <textarea value={form.medical_history ?? ''} onChange={(e) => updateField('medical_history', e.target.value)} />
            </label>
            <label>
              <span className="form-label">Daily Habits</span>
              <textarea value={form.daily_habits ?? ''} onChange={(e) => updateField('daily_habits', e.target.value)} />
            </label>
            <label>
              <span className="form-label">Care Notes</span>
              <textarea value={form.care_notes ?? ''} onChange={(e) => updateField('care_notes', e.target.value)} />
            </label>
            <label>
              <span className="form-label">Location Notes</span>
              <textarea value={form.location_notes ?? ''} onChange={(e) => updateField('location_notes', e.target.value)} />
            </label>
            {editingId && (
              <label>
                <span className="form-label">Transfer Destination</span>
                <input value={transferDestination} onChange={(e) => setTransferDestination(e.target.value)} placeholder="Facility or hospital name" />
              </label>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
            <button className="btn-primary" type="submit">{editingId ? 'Save Changes' : 'Register Resident'}</button>
            {editingId && <button className="btn-secondary" type="button" onClick={transfer}>Transfer & Pause</button>}
            <button className="btn-secondary" type="button" onClick={reset}>Clear</button>
          </div>
        </form>
      </div>
    </div>
  );
}
