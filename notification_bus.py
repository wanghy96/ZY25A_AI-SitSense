import streamlit as st

class NotificationBus:
    def __init__(self):
        self.listeners = {}
    
    def publish(self, event_name):
        """发布事件"""
        if event_name in self.listeners:
            for callback in self.listeners[event_name]:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in event listener: {e}")
    
    def subscribe(self, event_name, callback):
        """订阅事件"""
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(callback)
    
    def attach_streamlit_context(self):
        """附加Streamlit上下文"""
        if 'notification_bus' not in st.session_state:
            st.session_state.notification_bus = self

# 创建全局通知总线实例
notification_bus = NotificationBus()