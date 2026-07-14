"use client";

import { useEffect, useState, useRef } from "react";
import { Bell, CheckCircle2, AlertTriangle, Info, XCircle, Check } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface Notification {
  id: string;
  user_id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message: string;
  read: boolean;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export function NotificationBell({ userId }: { userId: string }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const supabase = createClient();

  useEffect(() => {
    if (!userId) return;

    // Fetch initial notifications
    const fetchNotifications = async () => {
      const { data } = await supabase
        .from("app_notifications")
        .select("*")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(20);

      if (data) {
        setNotifications(data as Notification[]);
      }
    };

    fetchNotifications();

    // Subscribe to new realtime notifications
    const channel = supabase
      .channel(`notifications:${userId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "app_notifications",
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          const newNotif = payload.new as Notification;
          setNotifications((prev) => [newNotif, ...prev]);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, supabase]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    await fetch("/api/notifications/mark-read", { method: "PATCH" });
  };

  const getIcon = (type: Notification["type"]) => {
    switch (type) {
      case "success":
        return <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />;
      case "error":
        return <XCircle className="w-4 h-4 text-cronus-red flex-shrink-0 mt-0.5" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />;
      default:
        return <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 border-2 border-cronus-gray/30 hover:border-cronus-red transition-colors relative bg-cronus-surface flex items-center justify-center"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5 text-cronus-white" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-cronus-red text-cronus-white text-[10px] font-mono font-bold flex items-center justify-center border border-cronus-surface animate-pulse">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-cronus-surface border-2 border-cronus-gray/50 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.8)] z-50">
          <div className="p-3 border-b-2 border-cronus-gray/30 flex items-center justify-between bg-cronus-bg">
            <span className="font-mono text-xs uppercase font-bold tracking-widest text-cronus-white">
              Notifications ({unreadCount} unread)
            </span>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="font-mono text-[10px] uppercase text-cronus-red hover:underline flex items-center"
              >
                <Check className="w-3 h-3 mr-1" /> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-cronus-gray/10">
            {notifications.length === 0 ? (
              <div className="p-6 text-center font-mono text-xs uppercase text-cronus-gray">
                No notifications right now.
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`p-3 transition-colors ${notif.read ? "bg-cronus-surface opacity-75" : "bg-cronus-bg/60 border-l-2 border-l-cronus-red"}`}
                >
                  <div className="flex items-start space-x-3">
                    {getIcon(notif.type)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-sans font-bold text-sm text-cronus-white leading-tight truncate">
                          {notif.title}
                        </p>
                        <span className="font-mono text-[9px] text-cronus-gray flex-shrink-0 ml-2">
                          {new Date(notif.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <p className="font-mono text-xs text-cronus-gray/90 mt-1 line-clamp-2">
                        {notif.message}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
