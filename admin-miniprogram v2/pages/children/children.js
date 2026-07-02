// admin-miniprogram/pages/children/children.js
var request = require('../../utils/request.js').request;

Page({
  data: {
    keyword: '',
    childrenList: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    showChildModal: false,
    modalChild: null,
    modalUsers: [],
    modalLoading: false
  },

  onLoad: function () {
    this.loadChildren();
  },

  onPullDownRefresh: function () {
    this.setData({ page: 1, hasMore: true, childrenList: [] });
    this.loadChildren();
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.loadChildren(true);
    }
  },

  onSearchInput: function (e) {
    var that = this;
    clearTimeout(that._searchTimer);
    that._searchTimer = setTimeout(function () {
      that.setData({ keyword: e.detail.value, page: 1, hasMore: true, childrenList: [] });
      that.loadChildren();
    }, 300);
  },

  loadChildren: function (append) {
    var that = this;
    if (that.data.loading) return;
    that.setData({ loading: true });

    var data = { page: that.data.page, page_size: that.data.pageSize };
    if (that.data.keyword) data.keyword = that.data.keyword;

    request({
      url: '/api/v1/admin/children',
      method: 'GET',
      data: data
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return {
          child_id: item.child_id,
          name: item.name || '未命名',
          phone: item.phone || '未绑定手机',
          phoneMasked: maskPhone(item.phone),
          created_at: formatDate(item.created_at),
          initial: (item.name || '?').charAt(0),
          avatarColor: getChildAvatarColor(item.child_id)
        };
      });

      var newList = append ? that.data.childrenList.concat(items) : items;
      var total = res.total || 0;

      that.setData({
        childrenList: newList,
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

  // 点击子女卡片 → 查看绑定老人
  onChildTap: function (e) {
    var child = e.currentTarget.dataset.child;
    if (!child) return;
    this.setData({
      showChildModal: true,
      modalChild: child,
      modalUsers: [],
      modalLoading: true
    });

    var that = this;
    request({
      url: '/api/v1/admin/relations',
      method: 'GET',
      data: { child_id: child.child_id }
    }).then(function (res) {
      var items = res.items || [];
      var list = items.map(function (item) {
        var elderly = item.elderly || {};
        return {
          user_id: elderly.user_id,
          nickname: elderly.nickname || '未命名',
          phone: elderly.phone || '',
          phoneMasked: maskPhone(elderly.phone),
          relation: item.relation || '未知',
          initial: (elderly.nickname || '?').charAt(0),
          avatarColor: getAvatarColor(elderly.user_id)
        };
      });
      that.setData({ modalUsers: list, modalLoading: false });
    }).catch(function () {
      that.setData({ modalLoading: false });
    });
  },

  closeChildModal: function () {
    this.setData({ showChildModal: false, modalChild: null, modalUsers: [] });
  }
});

function maskPhone(phone) {
  if (!phone || phone.length < 7) return phone || '';
  return phone.substring(0, 3) + '****' + phone.substring(7);
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  var d = new Date(dateStr);
  var y = d.getFullYear();
  var m = (d.getMonth() + 1 + '').padStart(2, '0');
  var day = (d.getDate() + '').padStart(2, '0');
  return y + '-' + m + '-' + day;
}

var CHILD_AVATAR_COLORS = ['#f472b6', '#c084fc', '#fb923c', '#a78bfa', '#f9ab00', '#00d4aa'];
function getChildAvatarColor(id) {
  var idx = (id || 0) % CHILD_AVATAR_COLORS.length;
  return CHILD_AVATAR_COLORS[idx];
}

var AVATAR_COLORS = ['#1a73e8', '#34a853', '#ea4335', '#f9ab00', '#7c5cfc', '#00d4aa', '#f472b6', '#fb923c'];
function getAvatarColor(id) {
  var idx = (id || 0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}
