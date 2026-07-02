// admin-miniprogram/pages/users/users.js
var request = require('../../utils/request.js').request;

Page({
  data: {
    userTotal: 0,
    childrenTotal: 0,
    keyword: '',
    userList: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    showUserModal: false,
    modalUser: null,
    modalChildren: [],
    modalLoading: false
  },

  onLoad: function () {
    this.loadUsers();
    this.loadChildrenCount();
  },

  onShow: function () {},

  onPullDownRefresh: function () {
    this.setData({ page: 1, hasMore: true, userList: [] });
    this.loadUsers();
    this.loadChildrenCount();
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.loadUsers(true);
    }
  },

  onSearchInput: function (e) {
    var that = this;
    clearTimeout(that._searchTimer);
    that._searchTimer = setTimeout(function () {
      that.setData({ keyword: e.detail.value, page: 1, hasMore: true, userList: [] });
      that.loadUsers();
    }, 300);
  },

  loadUsers: function (append) {
    var that = this;
    if (that.data.loading) return;
    that.setData({ loading: true });

    var data = { page: that.data.page, page_size: that.data.pageSize };
    if (that.data.keyword) data.keyword = that.data.keyword;

    request({
      url: '/api/v1/admin/users',
      method: 'GET',
      data: data
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return {
          user_id: item.user_id,
          nickname: item.nickname || '未命名',
          phone: item.phone || '未绑定手机',
          phoneMasked: maskPhone(item.phone),
          online_status: item.online_status,
          status: item.status,
          last_heartbeat_at: formatTime(item.last_heartbeat_at),
          created_at: formatDate(item.created_at),
          initial: (item.nickname || '?').charAt(0),
          avatarColor: getAvatarColor(item.user_id)
        };
      });

      var newList = append ? that.data.userList.concat(items) : items;
      var total = res.total || 0;

      that.setData({
        userList: newList,
        userTotal: total,
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

  loadChildrenCount: function () {
    var that = this;
    request({
      url: '/api/v1/admin/children',
      method: 'GET',
      data: { page: 1, page_size: 1 }
    }).then(function (res) {
      that.setData({ childrenTotal: res.total || 0 });
    }).catch(function () {});
  },

  // 点击老人卡片 → 查看绑定子女
  onUserTap: function (e) {
    var user = e.currentTarget.dataset.user;
    if (!user) return;
    this.setData({
      showUserModal: true,
      modalUser: user,
      modalChildren: [],
      modalLoading: true
    });

    var that = this;
    request({
      url: '/api/v1/admin/relations',
      method: 'GET',
      data: { user_id: user.user_id }
    }).then(function (res) {
      var items = res.items || [];
      var list = items.map(function (item) {
        var child = item.child || {};
        return {
          child_id: child.child_id,
          name: child.name || '未命名',
          phone: child.phone || '',
          phoneMasked: maskPhone(child.phone),
          relation: item.relation || '未知',
          initial: (child.name || '?').charAt(0),
          avatarColor: getChildAvatarColor(child.child_id)
        };
      });
      that.setData({ modalChildren: list, modalLoading: false });
    }).catch(function () {
      that.setData({ modalLoading: false });
    });
  },

  closeUserModal: function () {
    this.setData({ showUserModal: false, modalUser: null, modalChildren: [] });
  }
});

function maskPhone(phone) {
  if (!phone || phone.length < 7) return phone || '';
  return phone.substring(0, 3) + '****' + phone.substring(7);
}

function formatTime(timeStr) {
  if (!timeStr) return '';
  var d = new Date(timeStr);
  var now = new Date();
  var diff = now - d;
  if (diff < 60000) return '刚刚在线';
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前在线';
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前在线';
  return formatDate(timeStr);
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  var y = d.getFullYear();
  var m = (d.getMonth() + 1 + '').padStart(2, '0');
  var day = (d.getDate() + '').padStart(2, '0');
  return y + '-' + m + '-' + day;
}

var AVATAR_COLORS = ['#1a73e8', '#34a853', '#ea4335', '#f9ab00', '#7c5cfc', '#00d4aa', '#f472b6', '#fb923c'];
function getAvatarColor(id) {
  var idx = (id || 0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

var CHILD_AVATAR_COLORS = ['#f472b6', '#c084fc', '#fb923c', '#a78bfa', '#f9ab00', '#00d4aa'];
function getChildAvatarColor(id) {
  var idx = (id || 0) % CHILD_AVATAR_COLORS.length;
  return CHILD_AVATAR_COLORS[idx];
}
