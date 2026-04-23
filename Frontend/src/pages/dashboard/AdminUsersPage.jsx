import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer,
  BarChart, Bar, Cell 
} from "recharts";
import {
  Users, 
  RefreshCw, 
  UserCheck, 
  UserX, 
  Crown, 
  Trash2, 
  Shield,
  Search, 
  ChevronLeft, 
  ChevronRight, 
  AlertTriangle, 
  BarChart2, 
  Star,
  Zap,
  Mail,
  Bell,
  Send,
  MoreVertical
} from "lucide-react";
import { 
  getAdminUsers, 
  toggleUserStatus, 
  deleteUser, 
  getUserAnalyticsForAdmin,
  sendAdminNotification 
} from "../../api/adminApi";
import { toast } from "react-hot-toast";

export const AdminUsersPage = () => {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [search, setSearch] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [analyticsDays, setAnalyticsDays] = useState(14);
  const [notifyingUser, setNotifyingUser] = useState(null);
  const [notifContent, setNotifContent] = useState({ title: "Security Alert: High Spam Activity", message: "", type: "security" });
  const [sendingNotif, setSendingNotif] = useState(false);

  const PAGE_SIZE = 10;

  const fetchUsers = useCallback(async (p = page) => {
    setLoading(true);
    try {
      const data = await getAdminUsers(p, PAGE_SIZE);
      setUsers(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast.error("User matrix retrieval failed.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchUsers(); }, [page]);

  const handleToggle = async (userId, currentActive) => {
    setToggling(userId);
    try {
      await toggleUserStatus(userId, !currentActive);
      toast.success(`Entity status synchronized.`);
      fetchUsers();
    } catch (err) {
      toast.error("Status synchronization failed.");
    } finally {
      setToggling(null);
    }
  };

  const handleDelete = async (user) => {
    setConfirmDelete(null);
    setDeleting(user.id);
    try {
      await deleteUser(user.id);
      toast.success(`Entity "${user.username}" purged.`);
      fetchUsers();
    } catch (err) {
      toast.error("Entity purge failed.");
    } finally {
      setDeleting(null);
    }
  };

  const handleViewAnalytics = async (user) => {
    setSelectedUser(user);
    setAnalyticsDays(14);
    setLoadingStats(true);
    try {
      const data = await getUserAnalyticsForAdmin(user.id, 14);
      if (data && data.points) {
        const chartData = data.points.map(p => ({
          date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
          spam: p.spam_count,
          ham: p.ham_count
        }));
        setUserStats(chartData);
      }
    } catch {
      toast.error("Failed to load entity analytics.");
    } finally {
      setLoadingStats(false);
    }
  };

  const changeAnalyticsDays = async (days) => {
    setAnalyticsDays(days);
    if (!selectedUser) return;
    setLoadingStats(true);
    try {
      const data = await getUserAnalyticsForAdmin(selectedUser.id, days);
      if (data && data.points) {
        const chartData = data.points.map(p => ({
          date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
          spam: p.spam_count,
          ham: p.ham_count
        }));
        setUserStats(chartData);
      }
    } catch {
      toast.error("Failed to update entity analytics.");
    } finally {
      setLoadingStats(false);
    }
  };

  const handleSendNotification = async (e) => {
    e.preventDefault();
    if (!notifContent.message.trim()) return toast.error("Transmission payload cannot be empty.");
    setSendingNotif(true);
    try {
      await sendAdminNotification({
        userId: notifyingUser.id,
        ...notifContent
      });
      toast.success(`Security alert dispatched to ${notifyingUser.username}.`);
      setNotifyingUser(null);
      setNotifContent({ title: "Security Alert: High Spam Activity", message: "", type: "security" });
    } catch {
      toast.error("Failed to transmit security alert.");
    } finally {
      setSendingNotif(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="max-w-7xl mx-auto space-y-12 pb-24">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase text-indigo-400">
            <Users size={14} /> Entity Management
          </div>
          <h1 className="text-5xl font-black text-slate-900 tracking-tighter">
            User <span className="text-blue-600 font-semibold">Matrix</span>
          </h1>
          <p className="text-slate-500 max-w-xl font-medium">
            Oversee all registered entities, roles, and historical activity logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
            <input 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search entities..."
              className=" pl-11 pr-4 h-12 rounded-xl border-slate-200 text-sm text-slate-900 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 transition-all w-64"
            />
          </div>
          <button 
            onClick={() => fetchUsers()}
            className=" p-3 rounded-xl border-slate-200 text-slate-500 hover:text-slate-900 transition-all"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* User Grid */}
      <div className=" rounded-3xl border border-slate-200 shadow-md overflow-hidden">
        <div className="grid grid-cols-12 gap-6 px-8 py-4 bg-slate-50 border-b border-slate-100 text-[10px] font-black tracking-[0.2em] text-slate-500 uppercase">
          <div className="col-span-3">Entity Details</div>
          <div className="col-span-2 text-center">Authorization</div>
          <div className="col-span-3 text-center">Activity Metrics</div>
          <div className="col-span-2 text-center">Status</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>

        <div className="min-h-[400px]">
          <AnimatePresence mode="wait">
            {loading ? (
              <div className="h-[400px] flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {users.map((u, i) => (
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    key={u.id}
                    className="grid grid-cols-12 gap-6 px-8 py-6 items-center hover:bg-white/[0.02] transition-colors group"
                  >
                    <div className="col-span-3 flex gap-4 items-center">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-sm font-black text-slate-900 shadow-lg">
                        {u.username?.[0]?.toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-slate-900 truncate">{u.username}</p>
                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1 flex items-center gap-2">
                          <Mail size={10} /> {u.email}
                        </p>
                      </div>
                    </div>

                    <div className="col-span-2 flex justify-center">
                      {u.role === "admin" ? (
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[9px] font-black uppercase tracking-widest shadow-[0_0_10px_rgba(245,158,11,0.1)]">
                          <Crown size={12} /> Admin
                        </div>
                      ) : (
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-700 text-slate-500 text-[9px] font-black uppercase tracking-widest">
                          <Shield size={12} /> User
                        </div>
                      )}
                    </div>

                    <div className="col-span-3 flex flex-col items-center gap-2">
                      <div className="flex justify-between w-full max-w-[120px] text-[10px] font-bold">
                        <span className="text-rose-400">{u.spam_count || 0}</span>
                        <span className="text-slate-500">/</span>
                        <span className="text-emerald-400">{u.ham_count || 0}</span>
                      </div>
                      <div className="w-32 h-1 bg-slate-50 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-cyan-500 shadow-[0_0_8px_currentColor]" 
                          style={{ width: `${Math.min(100, ((u.prediction_count || 0) / 100) * 100)}%` }} 
                        />
                      </div>
                    </div>

                    <div className="col-span-2 flex justify-center">
                      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${u.is_active ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border-rose-500/20 text-rose-400"} text-[9px] font-black uppercase tracking-widest`}>
                        {u.is_active ? "Active" : "Locked"}
                      </div>
                    </div>

                    <div className="col-span-2 flex justify-end gap-2">
                      <button 
                        onClick={() => {
                          setNotifyingUser(u);
                          const ratio = (u.spam_count || 0) / (u.prediction_count || 1);
                          if (ratio > 0.35) {
                            setNotifContent({
                              title: "Urgent Security Protocol",
                              message: `Our neural core has detected that ${((u.spam_count/u.prediction_count)*100).toFixed(0)}% of your incoming traffic is malicious. Please exercise extreme caution with recent messages.`,
                              type: "security"
                            });
                          }
                        }}
                        className="p-2 rounded-xl border border-slate-100 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                        title="Dispatch Alert"
                      >
                        <Bell size={16} />
                      </button>
                      <button 
                        onClick={() => handleViewAnalytics(u)}
                        className="p-2 rounded-xl border border-slate-100 text-slate-500 hover:text-cyan-400 hover:bg-cyan-500/10 transition-all"
                        title="View Analytics"
                      >
                        <BarChart2 size={16} />
                      </button>
                      <button 
                        onClick={() => handleToggle(u.id, u.is_active)}
                        className={`p-2 rounded-xl border border-slate-100 hover:text-slate-900 transition-all ${u.is_active ? "text-rose-400 hover:bg-rose-500/10" : "text-emerald-400 hover:bg-emerald-500/10"}`}
                      >
                        {u.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                      </button>
                      <button 
                        onClick={() => setConfirmDelete(u)}
                        className="p-2 rounded-xl border border-slate-100 text-slate-600 hover:text-rose-500 hover:bg-rose-500/10 transition-all"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </AnimatePresence>
        </div>

        {/* Pagination */}
        <div className="p-6 bg-white/[0.02] border-t border-slate-100 flex justify-between items-center">
          <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button 
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="p-2  border-slate-200 rounded-xl disabled:opacity-30 hover:text-slate-900 transition-all"
            >
              <ChevronLeft size={20} />
            </button>
            <button 
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="p-2  border-slate-200 rounded-xl disabled:opacity-30 hover:text-slate-900 transition-all"
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      <AnimatePresence>
        {confirmDelete && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setConfirmDelete(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="relative w-full max-w-md  p-8 rounded-3xl border border-rose-500/30 shadow-md space-y-6"
            >
              <div className="flex items-center gap-4 text-rose-400">
                <div className="p-3 bg-rose-500/10 rounded-2xl border border-rose-500/20">
                  <AlertTriangle size={24} />
                </div>
                <h3 className="text-xl font-bold text-slate-900">Confirm Purge</h3>
              </div>
              
              <p className="text-sm text-slate-500 leading-relaxed">
                You are about to permanently purge entity <span className="text-slate-900 font-bold">{confirmDelete.username}</span> from the matrix. All associated telemetry and packet logs will be erased.
              </p>

              <div className="flex gap-4">
                <button 
                  onClick={() => setConfirmDelete(null)}
                  className="flex-1 h-12  border-slate-200 rounded-xl text-xs font-black uppercase tracking-widest hover:text-slate-900"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => handleDelete(confirmDelete)}
                  className="flex-1 h-12 bg-rose-500 text-slate-900 rounded-xl text-xs font-black uppercase tracking-widest shadow-lg  hover:bg-rose-600"
                >
                  Purge Entity
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* User Analytics Modal */}
      <AnimatePresence>
        {selectedUser && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedUser(null)}
              className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="relative w-full max-w-4xl bg-white p-10 rounded-[40px] border border-slate-200 shadow-xl space-y-8"
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-5">
                  <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-2xl font-black text-slate-900 shadow-md">
                    {selectedUser.username?.[0]?.toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-3xl font-black text-slate-900 tracking-tighter">{selectedUser.username}</h3>
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mt-1">{selectedUser.email}</p>
                  </div>
                </div>
                <button 
                  onClick={() => setSelectedUser(null)}
                  className="p-3  rounded-2xl border-slate-200 text-slate-500 hover:text-slate-900 transition-all"
                >
                  <RefreshCw size={20} />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-6">
                <div className=" p-6 rounded-3xl border-slate-100">
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Total Scans</p>
                  <h4 className="text-2xl font-black text-slate-900">{selectedUser.prediction_count}</h4>
                </div>
                <div className=" p-6 rounded-3xl border-slate-100">
                  <p className="text-[10px] font-black text-rose-500 uppercase tracking-widest mb-1">Spam Detected</p>
                  <h4 className="text-2xl font-black text-slate-900">{selectedUser.spam_count}</h4>
                </div>
                <div className=" p-6 rounded-3xl border-slate-100">
                  <p className="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-1">Clean Messages</p>
                  <h4 className="text-2xl font-black text-slate-900">{selectedUser.ham_count}</h4>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex justify-between items-end">
                  <div>
                    <h5 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <Zap className="text-cyan-400 w-4 h-4" />
                      {analyticsDays === 365 ? '1-Year' : `${analyticsDays}-Day`} Traffic Telemetry
                    </h5>
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Daily classification density breakdown</p>
                  </div>
                  <div className="flex bg-slate-50 p-1 rounded-xl border border-slate-100">
                    {[
                      { l: '7D', v: 7 },
                      { l: '14D', v: 14 },
                      { l: '1M', v: 30 },
                      { l: '1Y', v: 365 }
                    ].map(t => (
                      <button
                        key={t.v}
                        onClick={() => changeAnalyticsDays(t.v)}
                        className={`px-3 py-1.5 rounded-lg text-[10px] font-black transition-all ${
                          analyticsDays === t.v 
                            ? 'bg-cyan-500 text-black shadow-lg ' 
                            : 'text-slate-500 hover:text-slate-900'
                        }`}
                      >
                        {t.l}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="h-[300px] w-full bg-white rounded-3xl p-6 border border-slate-100 shadow-sm">
                  {loadingStats ? (
                    <div className="h-full flex items-center justify-center">
                      <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
                    </div>
                  ) : userStats ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={userStats}>
                        <defs>
                          <linearGradient id="userSpam" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.2}/>
                            <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="userHam" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />
                        <XAxis dataKey="date" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                        <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                        <ChartTooltip 
                          contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: "10px", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                        />
                        <Area type="monotone" dataKey="spam" stroke="#f43f5e" fillOpacity={1} fill="url(#userSpam)" strokeWidth={2} />
                        <Area type="monotone" dataKey="ham" stroke="#3b82f6" fillOpacity={1} fill="url(#userHam)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-slate-500 text-xs">No telemetry data available for this period.</div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Dispatch Alert Modal */}
      <AnimatePresence>
        {notifyingUser && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setNotifyingUser(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="relative w-full max-w-lg  p-8 rounded-[32px] border border-slate-200 shadow-md space-y-6"
            >
              <div className="flex items-center gap-4">
                <div className="p-3 bg-rose-500/10 rounded-2xl border border-rose-500/20 text-rose-400">
                  <Bell size={24} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900">Dispatch Security Alert</h3>
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Recipient: {notifyingUser.username}</p>
                </div>
              </div>

              <form onSubmit={handleSendNotification} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Alert Title</label>
                  <input 
                    value={notifContent.title}
                    onChange={(e) => setNotifContent({...notifContent, title: e.target.value})}
                    className="input-base w-full h-12 text-sm"
                    placeholder="Security Breach Detected"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Message Content</label>
                  <textarea 
                    value={notifContent.message}
                    onChange={(e) => setNotifContent({...notifContent, message: e.target.value})}
                    className="input-base w-full h-32 text-sm p-4 resize-none"
                    placeholder="Enter warning details..."
                  />
                </div>
                <div className="flex gap-4 pt-2">
                  <button 
                    type="button"
                    onClick={() => setNotifyingUser(null)}
                    className="flex-1 h-12  border-slate-200 rounded-xl text-xs font-black uppercase tracking-widest hover:text-slate-900"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit"
                    disabled={sendingNotif}
                    className="flex-1 h-12 bg-rose-500 text-slate-900 rounded-xl text-xs font-black uppercase tracking-widest shadow-lg  hover:bg-rose-600 flex items-center justify-center gap-2"
                  >
                    {sendingNotif ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <><Send size={14} /> Dispatch</>
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
