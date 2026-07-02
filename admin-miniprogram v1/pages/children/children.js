// admin-miniprogram/pages/children/children.js
var request = require('../../utils/request.js').request;

Page({
  data: {
    keyword: '',
    childrenList: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false
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
