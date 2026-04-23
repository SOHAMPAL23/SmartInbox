import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogOut, LayoutDashboard, UserCircle, ShieldAlert } from "lucide-react";
import { clsx } from "clsx";
import { Sidebar } from "../layout/Sidebar";

export const Layout = () => {
    return (
        <div className="flex h-screen bg-[#F8FAFC] overflow-hidden text-slate-800">
            {/* Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="flex-1 overflow-x-hidden overflow-y-auto">
                <div className="relative h-full flex flex-col p-8">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};
