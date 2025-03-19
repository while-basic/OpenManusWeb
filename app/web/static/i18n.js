// i18n.js - 国际化模块，管理中英文翻译

// 支持的语言
export const SUPPORTED_LANGUAGES = {
    'zh-CN': '中文',
    'en-US': 'English'
};

// 翻译文本
export const translations = {
    // 中文翻译
    'zh-CN': {
        // 页面标题和头部
        'page_title': 'Sith Web - 网页版',
        'app_title': 'Sith',
        'app_subtitle': 'AI智能助手 - 网页版',
        
        // 主要区域标题
        'processing_progress': '处理进度',
        'ai_thinking_process': 'AI思考过程',
        'workspace_files': '工作区文件',
        'conversation': '对话',
        
        // 按钮和控件
        'auto_scroll': '自动滚动',
        'clear': '清空',
        'refresh': '刷新',
        'send': '发送',
        'stop': '停止',
        'close': '关闭',
        
        // 状态和提示
        'records_count': '{count} Entry',
        'refresh_countdown': '{seconds}秒后刷新',
        'processing_request': '正在处理您的请求...',
        'processing_stopped': '处理已停止',
        'processing_failed': '处理失败',
        'file_name': '文件名',
        'no_workspace_files': '没有工作区文件',
        
        // 输入框占位符
        'input_placeholder': '输入您的问题或指令...',
        
        // 页脚
        'ui_made_by': 'Web界面制作:',
        'powered_by': 'Powered by Sith -',
        'creator_name': '云栖AI',
        
        // 错误消息
        'api_error': 'API错误',
        'send_message_error': '发送消息错误: {message}',
        'send_message_error_generic': '发送消息失败，请稍后再试',
        'stop_processing_error': '停止处理错误: {message}',
        'stop_processing_error_generic': '停止处理失败，请刷新页面',
        'load_files_error': '加载文件列表错误: {message}',
        'load_files_error_generic': '无法加载文件列表',
        'load_file_error': '加载文件内容错误: {message}',
        'load_file_error_generic': '无法加载文件: {file}',
        'file_empty_error': '文件内容为空',
        'websocket_error': '与服务器的连接中断',
        'server_error': '服务器发生错误',
        'already_processing': '已经在处理中，请等待完成',
        
        // 系统消息
        'error_occurred': '发生错误: {message}',
        'processing_in_progress': '正在处理中，请等待...',
        'processing_stopped_message': '已停止处理',
        
        // 语言切换
        'language': '语言',
        'switch_language': '切换语言',
        
        // 终端功能
        'terminal_command': '终端命令',
        'terminal_input_placeholder': '输入命令...',
        'run': '运行',
        'interrupt': '中断',
        'command_running': '命令执行中...',
        'command_completed': '命令已完成',
        'command_error': '命令执行错误: {message}',
        'terminal_title': '终端'
    },
    
    // 英文翻译
    'en-US': {
        // 页面标题和头部
        'page_title': 'Sith Web - Web Version',
        'app_title': 'Sith',
        'app_subtitle': 'AI Assistant - Web Version',
        
        // 主要区域标题
        'processing_progress': 'Processing Progress',
        'ai_thinking_process': 'AI Thinking Process',
        'workspace_files': 'Workspace Files',
        'conversation': 'Conversation',
        
        // 按钮和控件
        'auto_scroll': 'Auto Scroll',
        'clear': 'Clear',
        'refresh': 'Refresh',
        'send': 'Send',
        'stop': 'Stop',
        'close': 'Close',
        
        // 状态和提示
        'records_count': '{count} Records',
        'refresh_countdown': 'Refresh in {seconds}s',
        'processing_request': 'Processing your request...',
        'processing_stopped': 'Processing stopped',
        'processing_failed': 'Processing failed',
        'file_name': 'File Name',
        'no_workspace_files': 'No workspace files',
        
        // 输入框占位符
        'input_placeholder': 'Enter your question or instruction...',
        
        // 页脚
        'ui_made_by': 'UI Made by:',
        'powered_by': 'Powered by Sith -',
        'creator_name': '云栖AI',
        
        // 错误消息
        'api_error': 'API Error',
        'send_message_error': 'Send message error: {message}',
        'send_message_error_generic': 'Failed to send message, please try again',
        'stop_processing_error': 'Stop processing error: {message}',
        'stop_processing_error_generic': 'Failed to stop processing, please refresh the page',
        'load_files_error': 'Error loading file list: {message}',
        'load_files_error_generic': 'Failed to load file list',
        'load_file_error': 'Error loading file: {message}',
        'load_file_error_generic': 'Failed to load file: {file}',
        'file_empty_error': 'File content is empty',
        'websocket_error': 'Connection to server lost',
        'server_error': 'Server encountered an error',
        'already_processing': 'Already processing, please wait for completion',
        
        // 系统消息
        'error_occurred': 'Error occurred: {message}',
        'processing_in_progress': 'Processing in progress, please wait...',
        'processing_stopped_message': 'Processing has been stopped',
        
        // 语言切换
        'language': 'Language',
        'switch_language': 'Switch Language',
        
        // 终端功能
        'terminal_command': 'Terminal Command',
        'terminal_input_placeholder': 'Enter command...',
        'run': 'Run',
        'interrupt': 'Interrupt',
        'command_running': 'Command running...',
        'command_completed': 'Command completed',
        'command_error': 'Command execution error: {message}',
        'terminal_title': 'Terminal'
    }
};

// 当前语言
let currentLanguage = 'en-US';

// 获取浏览器语言
export function getBrowserLanguage() {
    const browserLang = navigator.language || navigator.userLanguage;
    // 如果浏览器语言以'zh'开头，返回中文，否则返回英文
    return browserLang.startsWith('zh') ? 'zh-CN' : 'en-US';
}

// 设置当前语言
export function setLanguage(lang) {
    if (translations[lang]) {
        currentLanguage = lang;
        // 保存语言选择到本地存储
        localStorage.setItem('language', lang);
        return true;
    }
    return false;
}

// 获取当前语言
export function getCurrentLanguage() {
    return currentLanguage;
}

// 初始化语言
export function initLanguage() {
    // 尝试从本地存储中获取语言设置
    const savedLang = localStorage.getItem('language');
    // 如果本地存储有语言设置，使用保存的设置；否则尝试使用浏览器语言
    if (savedLang && translations[savedLang]) {
        currentLanguage = savedLang;
    } else {
        currentLanguage = getBrowserLanguage();
    }
    return currentLanguage;
}

// 获取翻译文本
export function t(key, params = {}) {
    // 获取当前语言的翻译
    const lang = translations[currentLanguage] || translations['en-US'];
    let text = lang[key] || key;
    
    // 替换参数
    if (params) {
        for (const [key, value] of Object.entries(params)) {
            text = text.replace(new RegExp(`{${key}}`, 'g'), value);
        }
    }
    
    return text;
}

// 更新页面文本
export function updatePageTexts() {
    // 更新页面标题
    document.title = t('page_title');
    
    // 更新所有带有data-i18n属性的元素
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(element => {
        const key = element.getAttribute('data-i18n');
        
        // 如果是输入元素（如input, textarea），更新placeholder
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            if (element.hasAttribute('placeholder')) {
                element.placeholder = t(key);
            }
        } 
        // 否则更新元素内容
        else {
            element.textContent = t(key);
        }
    });
}
