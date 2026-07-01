// admin-miniprogram/pages/audit/audit.js
var request = require('../../utils/request.js').request;
var config = require('../../config/index.js');

Page({
  data: {
    operation: '',
    operatorType: '',
    auditList: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    exporting: false
  },

  onLoad: function () {
    this.loadAudit();
  },

  onPullDownRefresh: function () {
    this.setData({ page: 1, hasMore: true, auditList: [] });
    this.loadAudit();
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.loadAudit(true);
    }
  },

  onFilterOperation: function () {
    var that = this;
    wx.showActionSheet({
      itemList: ['全部', '登录', '问答', '绑定'],
      success: function (res) {
        var map = { 0: '', 1: 'login', 2: 'ask', 3: 'bind' };
        var val = map[res.tapIndex] || '';
        that.setData({ operation: val, page: 1, hasMore: true, auditList: [] });
        that.loadAudit();
      }
    });
  },

  onFilterOperator: function () {
    var that = this;
    wx.showActionSheet({
      itemList: ['全部', '老人', '子女', '管理员', '系统'],
      success: function (res) {
        var map = { 0: '', 1: 'user', 2: 'child', 3: 'admin', 4: 'system' };
        var val = map[res.tapIndex] || '';
        that.setData({ operatorType: val, page: 1, hasMore: true, auditList: [] });
        that.loadAudit();
      }
    });
  },

  loadAudit: function (append) {
    var that = this;
    if (that.data.loading) return;
    that.setData({ loading: true });

    var data = { page: that.data.page, page_size: that.data.pageSize };
    if (that.data.operation) data.operation = that.data.operation;
    if (that.data.operatorType) data.operator_type = that.data.operatorType;

    request({
      url: '/admin/audit',
      method: 'GET',
      data: data
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return {
          id: item.id || item.audit_id,
          operation: item.operation || item.action || '未知操作',
          operator_type: item.operator_type || item.operatorType || '',
          operator_name: item.operator_name || item.operatorName || '',
          created_at: formatDateTime(item.created_at)
        };
      });

      var newList = append ? that.data.auditList.concat(items) : items;
      var total = res.total || 0;

      that.setData({
        auditList: newList,
        page: that.data.page + (append ? 1 : 1),
        hasMore: newList.length < total,
        loading: false
      });
      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false });
      wx.stopPullDownRefresh();
    });
  },

  handleExport: function () {
    var that = this;
    if (that.data.exporting) return;
    that.setData({ exporting: true });

    var params = [];
    if (that.data.operation) params.push('operation=' + that.data.operation);
    if (that.data.operatorType) params.push('operator_type=' + that.data.operatorType);
    params.push('format=csv');
    var query = params.join('&');

    var downloadUrl = config.baseUrl + '/admin/audit/export?' + query;

    wx.showLoading({ title: '导出中...' });
    wx.downloadFile({
      url: downloadUrl,
      header: {
        'Authorization': 'Bearer ' + (getApp().globalData.token || '')
      },
      success: function (res) {
        wx.hideLoading();
        if (res.statusCode === 200) {
          wx.openDocument({
            filePath: res.tempFilePath,
            showMenu: true,
            success: function () {},
            fail: function () {
              wx.showToast({ title: '打开文件失败', icon: 'none' });
            }
          });
        } else {
          wx.showToast({ title: '导出失败', icon: 'none' });
        }
      },
      fail: function () {
        wx.hideLoading();
        wx.showToast({ title: '网络异常，导出失败', icon: 'none' });
      },
      complete: function () {
        that.setData({ exporting: false });
      }
    });
  }
});

function formatDateTime(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  var y = d.getFullYear();
  var m = (d.getMonth() + 1 + '').padStart(2, '0');
  var day = (d.getDate() + '').padStart(2, '0');
  var h = (d.getHours() + '').padStart(2, '0');
  var min = (d.getMinutes() + '').padStart(2, '0');
  var s = (d.getSeconds() + '').padStart(2, '0');
  return y + '-' + m + '-' + day + ' ' + h + ':' + min + ':' + s;
}
